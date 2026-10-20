const encoder = new TextEncoder()

// Límite de la especificación PDF. Preview en macOS y Chrome rechazan páginas mayores.
const MAX_PAGE = 14400

export function pdfFromJpeg(jpeg: Uint8Array, width: number, height: number): Uint8Array {
  const pixelWidth = Math.max(1, Math.round(width))
  const pixelHeight = Math.max(1, Math.round(height))
  const fit = Math.min(1, MAX_PAGE / Math.max(pixelWidth, pixelHeight))
  const pageWidth = Math.max(1, Math.round(pixelWidth * fit))
  const pageHeight = Math.max(1, Math.round(pixelHeight * fit))
  const chunks: Uint8Array[] = []
  let cursor = 0
  const offsets: number[] = []
  const add = (bytes: Uint8Array) => {
    chunks.push(bytes)
    cursor += bytes.length
  }
  const addText = (value: string) => add(encoder.encode(value))
  const objectStart = (body: string) => {
    offsets.push(cursor)
    addText(body)
  }

  // El comentario binario evita que el sistema trate el archivo como texto.
  addText("%PDF-1.4\n%")
  add(new Uint8Array([0xe2, 0xe3, 0xcf, 0xd3, 0x0a]))
  objectStart("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
  objectStart("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
  objectStart(
    `3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] /Contents 4 0 R /Resources << /XObject << /Im 5 0 R >> >> >>\nendobj\n`,
  )
  const content = `q\n${pageWidth} 0 0 ${pageHeight} 0 0 cm\n/Im Do\nQ\n`
  objectStart(`4 0 obj\n<< /Length ${encoder.encode(content).length} >>\nstream\n${content}endstream\nendobj\n`)
  offsets.push(cursor)
  addText(
    `5 0 obj\n<< /Type /XObject /Subtype /Image /Width ${pixelWidth} /Height ${pixelHeight} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`,
  )
  add(jpeg)
  addText("\nendstream\nendobj\n")

  const xrefAt = cursor
  const size = offsets.length + 1
  let xref = `xref\n0 ${size}\n0000000000 65535 f \n`
  for (const offset of offsets) xref += `${offset.toString().padStart(10, "0")} 00000 n \n`
  xref += `trailer\n<< /Size ${size} /Root 1 0 R >>\nstartxref\n${xrefAt}\n%%EOF\n`
  addText(xref)

  const output = new Uint8Array(cursor)
  let written = 0
  for (const chunk of chunks) {
    output.set(chunk, written)
    written += chunk.length
  }
  return output
}
