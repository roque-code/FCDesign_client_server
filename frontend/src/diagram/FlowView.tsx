import {
  Background,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react"
import { useEffect, useMemo, useState, type CSSProperties } from "react"

import type { FlowGraph } from "../api"
import { spellText } from "../dialect"
import { useLocale, useT } from "../i18n"
import { saveDownload } from "../saveFile"
import { focusNodeId } from "./focus"
import { labelAnchor } from "./figures"
import { ShapeGlyph, SwitchGlyph } from "./glyphs"
import { layoutGraph } from "./layout"
import { pdfFromJpeg } from "./pdf"
import { buildSvg, type Drawing } from "./svg"
import "@xyflow/react/dist/style.css"

type SwitchCase = { label: string | null; width: number }
type ShapeData = { label: string; figure: string; active: boolean; width: number; height: number; cases: SwitchCase[] }
type RouteData = { points: Array<{ x: number; y: number }>; label: string | null }
type ShapeNode = Node<ShapeData, "shape">
type RouteEdge = Edge<RouteData, "route">

function Shape({ data }: NodeProps<ShapeNode>) {
  const locale = useLocale()
  if (data.figure === "switch") {
    return (
      <div className={`shape shape-switch${data.active ? " active" : ""}`} data-active={data.active ? "true" : "false"}>
        <Handle type="target" position={Position.Top} />
        <Handle type="source" position={Position.Bottom} />
        <SwitchGlyph width={data.width} height={data.height} cases={data.cases} active={data.active} />
        <span className="switch-title">{data.label}</span>
        <div className="switch-cases">
          {data.cases.map((item, index) => (
            <span key={`${item.label ?? "otro"}-${index}`} style={{ width: item.width }}>
              {spellText(locale, item.label ?? "De Otro Modo")}
            </span>
          ))}
        </div>
      </div>
    )
  }
  return (
    <div className={`shape shape-${data.figure}${data.active ? " active" : ""}`} data-active={data.active ? "true" : "false"}>
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
      <ShapeGlyph figure={data.figure} active={data.active} />
      {data.figure !== "join" && <span>{data.label}</span>}
    </div>
  )
}

function Route({ id, data, markerEnd }: EdgeProps<RouteEdge>) {
  const points = data?.points ?? []
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x},${point.y}`).join(" ")
  const anchor = labelAnchor(points)
  return (
    <>
      <BaseEdge id={id} path={path} style={{ stroke: "#c0392b", strokeWidth: 1.75 }} markerEnd={markerEnd} />
      {data?.label && anchor && (
        <EdgeLabelRenderer>
          <div className="edge-label" style={{ transform: `translate(-50%, -50%) translate(${anchor.x}px, ${anchor.y}px)` }}>
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}

const nodeTypes = { shape: Shape }
const edgeTypes = { route: Route }

function fileBase(name: string): string {
  const cleaned = name.replace(/[^\p{L}\p{N}_-]+/gu, "-").replace(/^-|-$/g, "")
  return cleaned || "diagrama"
}

function download(filename: string, blob: Blob) {
  void saveDownload(filename, blob)
}

async function raster(svg: string, width: number, height: number): Promise<HTMLCanvasElement> {
  const canvas = document.createElement("canvas")
  const scale = 2
  canvas.width = Math.max(1, Math.round(width * scale))
  canvas.height = Math.max(1, Math.round(height * scale))
  const context = canvas.getContext("2d")
  if (!context) throw new Error("Sin lienzo.")
  context.scale(scale, scale)
  context.fillStyle = "#fffdf8"
  context.fillRect(0, 0, width, height)
  const image = new Image()
  const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml;charset=utf-8" }))
  try {
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve()
      image.onerror = () => reject(new Error("No se pudo rasterizar el diagrama."))
      image.src = url
    })
    context.drawImage(image, 0, 0, width, height)
  } finally {
    URL.revokeObjectURL(url)
  }
  return canvas
}

export function FlowView({
  open,
  onToggle,
  graph,
  focusLine,
  theme,
  dirty,
  note,
  filename,
  onSelectLine,
}: {
  open: boolean
  onToggle: () => void
  graph: FlowGraph | null
  focusLine: number | null
  theme: "light" | "dark"
  dirty: boolean
  note: string
  filename: string
  onSelectLine: (line: number) => void
}) {
  const t = useT()
  const locale = useLocale()
  const [drawing, setDrawing] = useState<Drawing | null>(null)
  const [problem, setProblem] = useState("")
  const [printUrl, setPrintUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!graph) {
      setDrawing(null)
      return
    }
    let cancel = false
    setProblem("")
    void layoutGraph(graph, locale)
      .then((next) => {
        if (!cancel) setDrawing(next)
      })
      .catch(() => {
        if (!cancel) setProblem("layout")
      })
    return () => {
      cancel = true
    }
  }, [graph, locale])

  const svg = drawing ? buildSvg(drawing, locale) : ""

  useEffect(() => {
    if (!svg) {
      setPrintUrl(null)
      return
    }
    const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml;charset=utf-8" }))
    setPrintUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [svg])

  const focusId = graph ? focusNodeId(graph.nodes, focusLine) : null
  const nodes: ShapeNode[] = useMemo(
    () =>
      drawing?.nodes.map((node) => ({
        id: node.id,
        type: "shape",
        position: { x: node.x, y: node.y },
        width: node.width,
        height: node.height,
        measured: { width: node.width, height: node.height },
        handles: [
          { type: "target", position: Position.Top, x: node.width / 2, y: 0, width: 8, height: 8 },
          { type: "source", position: Position.Bottom, x: node.width / 2, y: node.height, width: 8, height: 8 },
        ],
        draggable: false,
        connectable: false,
        data: {
          label: node.text,
          figure: node.figure,
          active: node.id === focusId,
          width: node.width,
          height: node.height,
          cases: (node.cases ?? []).map((item) => ({ label: item.label, width: item.width })),
        },
        style: { width: node.width, height: node.height },
      })) ?? [],
    [drawing, focusId],
  )
  const edges: RouteEdge[] = useMemo(
    () =>
      drawing?.edges.map((edge, index) => ({
        id: `e${index}`,
        source: edge.source,
        target: edge.target,
        type: "route",
        markerEnd: { type: MarkerType.ArrowClosed, color: "#c0392b", width: 16, height: 16 },
        data: { points: edge.points, label: edge.label },
      })) ?? [],
    [drawing],
  )
  const canvasStyle = {
    "--flow-width": `${Math.ceil((drawing?.width ?? 8000) + 64)}px`,
    "--flow-height": `${Math.ceil((drawing?.height ?? 8000) + 64)}px`,
  } as CSSProperties

  async function exportSvg() {
    if (!svg) return
    download(`${fileBase(filename)}.svg`, new Blob([svg], { type: "image/svg+xml;charset=utf-8" }))
  }

  async function exportPng() {
    if (!drawing || !svg) return
    const canvas = await raster(svg, drawing.width, drawing.height)
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"))
    if (blob) download(`${fileBase(filename)}.png`, blob)
  }

  async function exportPdf() {
    if (!drawing || !svg) return
    const canvas = await raster(svg, drawing.width, drawing.height)
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92))
    if (!blob) return
    const bytes = new Uint8Array(await blob.arrayBuffer())
    const pdf = pdfFromJpeg(bytes, canvas.width, canvas.height)
    const page = pdf.buffer.slice(pdf.byteOffset, pdf.byteOffset + pdf.byteLength) as ArrayBuffer
    download(`${fileBase(filename)}.pdf`, new Blob([page], { type: "application/octet-stream" }))
  }

  return (
    <section className="diagram" id="diagrama" aria-label={t("diagram")}>
      <div className="diagram-toolbar">
        <div className="diagram-title">
          <h2>{t("diagram")}</h2>
          <button
            type="button"
            className="fold"
            aria-expanded={open}
            aria-controls="diagrama-contenido"
            aria-label={open ? t("hideDiagram") : t("showDiagram")}
            onClick={onToggle}
          >
            {open ? "−" : "+"}
          </button>
        </div>
        {open && (
          <>
            <button type="button" onClick={() => void exportSvg()} disabled={!drawing}>
              SVG
            </button>
            <button type="button" onClick={() => void exportPng()} disabled={!drawing}>
              PNG
            </button>
            <button type="button" onClick={() => void exportPdf()} disabled={!drawing}>
              PDF
            </button>
            <button type="button" onClick={() => window.print()} disabled={!drawing}>
              {t("print")}
            </button>
            {dirty && <span className="note">{t("diagramFollows")}</span>}
          </>
        )}
      </div>
      {open && (
        <div className="diagram-body" id="diagrama-contenido">
      {!graph && <p className="note">{note || t("noDiagram")}</p>}
      {problem && <p className="error">{problem === "layout" ? t("diagramLayout") : problem}</p>}
      {graph && drawing && (
        <div className="diagram-canvas" style={canvasStyle}>
          <ReactFlow
            key={graph.nodes.map((node) => node.text).join("|")}
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            fitViewOptions={{ padding: 0.16, minZoom: 0.1, maxZoom: 1.2 }}
            minZoom={0.1}
            maxZoom={1.6}
            colorMode={theme}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable
            proOptions={{ hideAttribution: false }}
            onNodeClick={(_, node) => {
              const line = graph.nodes.find((item) => item.id === node.id)?.line
              if (line != null) onSelectLine(line)
            }}
          >
            <Background />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      )}
      {printUrl && <img className="diagram-print" alt={t("diagramPrint")} src={printUrl} />}
        </div>
      )}
    </section>
  )
}
