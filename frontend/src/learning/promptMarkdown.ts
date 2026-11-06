/** Markdown corto y seguro para el enunciado de un reto. No interpreta HTML. */

const FIGURE = /^\/api\/v1\/learning\/figures\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/$/i

export function renderPrompt(source: string): string {
  const text = source.replaceAll("\r\n", "\n").replaceAll("\r", "\n")
  const parts: string[] = []
  const fence = /```[^\n`]*\n([\s\S]*?)```/g
  let last = 0
  for (const match of text.matchAll(fence)) {
    const index = match.index ?? 0
    parts.push(...flow(text.slice(last, index)))
    parts.push(`<pre><code>${escapeHtml(match[1].replace(/\n$/, ""))}</code></pre>`)
    last = index + match[0].length
  }
  parts.push(...flow(text.slice(last)))
  return parts.join("")
}

export function htmlToMarkdown(html: string): string {
  if (typeof DOMParser === "undefined") return ""
  const doc = new DOMParser().parseFromString(html, "text/html")
  doc.querySelectorAll("script, style").forEach((node) => node.remove())
  return walk(doc.body).replace(/\n{3,}/g, "\n\n").trim()
}

function flow(chunk: string): string[] {
  return chunk
    .split(/\n{2,}/)
    .map((piece) => block(piece.trim()))
    .filter((piece) => piece.length > 0)
}

function block(text: string): string {
  if (!text) return ""
  const lines = text.split("\n")
  const heading = /^(#{1,3})\s+(.+)$/.exec(lines[0])
  if (heading && lines.length === 1) return headingTag(heading[1].length, heading[2])
  if (heading) return `${headingTag(heading[1].length, heading[2])}${block(lines.slice(1).join("\n"))}`
  if (lines.every((line) => /^[-*]\s+\S/.test(line))) {
    return `<ul>${lines.map((line) => `<li>${inline(escapeHtml(line.replace(/^[-*]\s+/, "")))}</li>`).join("")}</ul>`
  }
  if (lines.every((line) => /^\d+\.\s+\S/.test(line))) {
    return `<ol>${lines.map((line) => `<li>${inline(escapeHtml(line.replace(/^\d+\.\s+/, "")))}</li>`).join("")}</ol>`
  }
  return `<p>${lines.map((line) => inline(escapeHtml(line))).join("<br>")}</p>`
}

function headingTag(marks: number, body: string): string {
  const level = marks + 1
  return `<h${level}>${inline(escapeHtml(body))}</h${level}>`
}

function inline(escaped: string): string {
  const codes: string[] = []
  let text = escaped.replace(/`([^`\n]+)`/g, (_full, code: string) => {
    codes.push(`<code>${code}</code>`)
    return `\u0000${codes.length - 1}\u0000`
  })
  text = text.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_full, alt: string, href: string) => {
    const src = safeHref(href)
    return src ? `<img src="${src}" alt="${alt}">` : `![${alt}](${href})`
  })
  text = text.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_full, label: string, href: string) => {
    const src = safeHref(href)
    return src ? `<a href="${src}" rel="noopener noreferrer">${label}</a>` : `[${label}](${href})`
  })
  text = text.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
  text = text.replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>")
  return text.replace(/\u0000(\d+)\u0000/g, (_full, index: string) => codes[Number(index)] ?? "")
}

function safeHref(raw: string): string | null {
  const href = raw.trim()
  if (FIGURE.test(href)) return href
  if (/^https:\/\/[^\s<>"]+$/i.test(href)) return href
  return null
}

function escapeHtml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
}

function walk(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? ""
  if (node.nodeType !== Node.ELEMENT_NODE) return ""
  const element = node as HTMLElement
  const tag = element.tagName.toLowerCase()
  const inner = [...element.childNodes].map(walk).join("")
  if (tag === "br") return "\n"
  if (tag === "strong" || tag === "b") return `**${inner.trim()}**`
  if (tag === "em" || tag === "i") return `*${inner.trim()}*`
  if (tag === "code") return `\`${inner.trim()}\``
  if (tag === "pre") return `\n\n\`\`\`\n${element.textContent ?? ""}\n\`\`\`\n\n`
  if (tag === "h1") return `\n\n# ${inner.trim()}\n\n`
  if (tag === "h2") return `\n\n## ${inner.trim()}\n\n`
  if (tag === "h3") return `\n\n### ${inner.trim()}\n\n`
  if (tag === "li") return `- ${inner.trim()}\n`
  if (tag === "p" || tag === "div") return `\n\n${inner.trim()}\n\n`
  if (tag === "a") {
    const href = element.getAttribute("href") ?? ""
    return safeHref(href) ? `[${inner.trim()}](${href})` : inner
  }
  if (tag === "img") {
    const src = element.getAttribute("src") ?? ""
    const alt = element.getAttribute("alt") ?? ""
    return safeHref(src) ? `![${alt}](${src})` : ""
  }
  return inner
}
