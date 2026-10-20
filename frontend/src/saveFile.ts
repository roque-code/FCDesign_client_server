type TauriWindow = Window & {
  __TAURI_INTERNALS__?: { invoke: (command: string, args: Record<string, unknown>) => Promise<unknown> }
}

const SAVE_ERROR = "No se pudo guardar el archivo."

function desktopInvoke(): TauriWindow["__TAURI_INTERNALS__"] | null {
  if (typeof window === "undefined") return null
  return (window as TauriWindow).__TAURI_INTERNALS__ ?? null
}

function report(message: string) {
  if (typeof window === "undefined") return
  window.dispatchEvent(new CustomEvent("traza-notice", { detail: message }))
}

function browserDownload(filename: string, blob: Blob) {
  // application/pdf hace que Chrome abra el visor y deje el archivo como
  // "Sin confirmar *.crdownload" en macOS, Windows y Linux. Un tipo genérico
  // obliga a guardarlo, y el blob tiene que seguir vivo hasta que el gestor
  // termine de copiarlo.
  const file = blob.type === "application/octet-stream" ? blob : new Blob([blob], { type: "application/octet-stream" })
  const url = URL.createObjectURL(file)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  link.rel = "noopener"
  document.body.append(link)
  link.click()
  window.setTimeout(() => {
    link.remove()
    URL.revokeObjectURL(url)
  }, 60_000)
}

function encodeBase64(bytes: Uint8Array): string {
  const parts: string[] = []
  const size = 0x8000
  for (let index = 0; index < bytes.length; index += size) {
    parts.push(String.fromCharCode(...bytes.subarray(index, index + size)))
  }
  return btoa(parts.join(""))
}

/** En el navegador usa la descarga habitual. En la aplicación abre el diálogo de guardar. */
export async function saveDownload(filename: string, body: Blob | string): Promise<void> {
  const blob = typeof body === "string" ? new Blob([body], { type: "text/plain;charset=utf-8" }) : body
  const invoke = desktopInvoke()
  if (!invoke) {
    browserDownload(filename, blob)
    return
  }
  try {
    const bytes = new Uint8Array(await blob.arrayBuffer())
    const saved = await invoke.invoke("save_download", { filename, data_base64: encodeBase64(bytes) })
    if (saved !== true && saved !== false) report(SAVE_ERROR)
  } catch (caught) {
    const message = typeof caught === "string" && caught ? caught : SAVE_ERROR
    report(message)
  }
}

export async function saveRemote(filename: string, href: string): Promise<void> {
  try {
    const response = await fetch(href)
    if (!response.ok) throw new Error(SAVE_ERROR)
    await saveDownload(filename, await response.blob())
  } catch (caught) {
    report(caught instanceof Error && caught.message ? caught.message : SAVE_ERROR)
  }
}
