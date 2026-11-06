import { describe, expect, it } from "vitest"

import { renderPrompt } from "./promptMarkdown"

describe("enunciado en markdown", () => {
  it("deja el texto plano en párrafos y conserva el salto de línea", () => {
    expect(renderPrompt("Lee un entero.\nEscribe el doble.")).toBe(
      "<p>Lee un entero.<br>Escribe el doble.</p>",
    )
  })

  it("dibuja título, negrita, código, lista e imagen del reto", () => {
    const html = renderPrompt(
      "## Ejemplo 1\n\nEl máximo es **49**.\n\n- un caso\n- otro caso\n\n![figura](/api/v1/learning/figures/11111111-1111-1111-1111-111111111111/)\n\n`height`",
    )
    expect(html).toContain("<h3>Ejemplo 1</h3>")
    expect(html).toContain("<strong>49</strong>")
    expect(html).toContain("<ul><li>un caso</li><li>otro caso</li></ul>")
    expect(html).toContain(
      '<img src="/api/v1/learning/figures/11111111-1111-1111-1111-111111111111/" alt="figura">',
    )
    expect(html).toContain("<code>height</code>")
  })

  it("no interpreta html ni enlaces que no sean https o una imagen propia", () => {
    const html = renderPrompt('<script>alert(1)</script>\n\n[malo](javascript:alert(1))\n\n![x](data:image/svg+xml,x)')
    expect(html).not.toContain("<script>")
    expect(html).toContain("&lt;script&gt;")
    expect(html).not.toContain("href=")
    expect(html).not.toContain("<img")
  })

  it("muestra un bloque de código tal como se escribió", () => {
    expect(renderPrompt("```\nheight = [1, 8]\n```")).toBe("<pre><code>height = [1, 8]</code></pre>")
  })
})
