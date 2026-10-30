import { useEffect, useLayoutEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type RefObject } from "react"

import type { Account } from "../api"
import { cameraToFit, clampScale, clientToWorld, snap, viewFrom, zoomAt, type Camera, type Point, type View } from "./geometry"
import { translate, useLocale, useT, type MessageKey } from "../i18n"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { LeaveSubjectButton } from "../subjects/leave"
import { ErCanvas } from "./ErCanvas"
import { accidentExample } from "./example"
import {
  applyCardinality,
  connectPair,
  createNode,
  edgeFamily,
  removeNode,
  type ConnectReason,
  type ErEdge,
  type ErNode,
  type LinkTool,
  type NodeKind,
  type Selection,
} from "./model"
import { Glyph, LineIcon } from "./shapes"
import { createEmpty, readStore, writeStore, type ErProject, type ErStore } from "./store"
import "./erd.css"

type Tool = "move" | LinkTool
type Gesture =
  | { type: "pan"; pointerId: number; x: number; y: number; cx: number; cy: number; scale: number }
  | { type: "node"; pointerId: number; id: string; ox: number; oy: number; moved: boolean; startX: number; startY: number }

const FIGURES: NodeKind[] = [
  "entity",
  "weak-entity",
  "relationship",
  "identifying",
  "attribute",
  "multivalued",
  "derived",
  "isa",
]

const TOOLS: Tool[] = ["move", "many-many", "many-one", "one-one", "partial", "total"]

const REASONS: Record<ConnectReason, MessageKey> = {
  same: "erdSame",
  exists: "erdExists",
  kind: "erdKind",
  "between-entities": "erdBetweenEntities",
}

function figureLabel(kind: NodeKind): MessageKey {
  switch (kind) {
    case "entity":
      return "erdEntity"
    case "weak-entity":
      return "erdWeakEntity"
    case "relationship":
      return "erdRelationship"
    case "identifying":
      return "erdIdentifying"
    case "attribute":
      return "erdAttribute"
    case "multivalued":
      return "erdMultivalued"
    case "derived":
      return "erdDerived"
    case "isa":
      return "erdIsa"
  }
}

function toolLabel(tool: Tool): MessageKey {
  switch (tool) {
    case "move":
      return "erdMove"
    case "many-many":
      return "erdManyMany"
    case "many-one":
      return "erdManyOne"
    case "one-one":
      return "erdOneOne"
    case "partial":
      return "erdPartial"
    case "total":
      return "erdTotal"
  }
}

function emptyStore(name: string): ErStore {
  const created = createEmpty(name)
  return { activeId: created.id, projects: [created] }
}

function nextName(projects: ErProject[], base: string): string {
  const names = new Set(projects.map((project) => project.name))
  if (!names.has(base)) return base
  let index = 2
  while (names.has(`${base} ${index}`)) index += 1
  return `${base} ${index}`
}

function otherEnd(edge: ErEdge, nodeId: string, nodes: ErNode[]): string {
  const other = nodes.find((item) => item.id === (edge.source === nodeId ? edge.target : edge.source))
  const card = edge.min !== "" && edge.max !== "" ? ` ${edge.min}..${edge.max}` : ""
  return `${other?.label ?? ""}${card}`
}

function Inspector({
  node,
  edge,
  nodes,
  edges,
  nameRef,
  onNode,
  onEdge,
  onDelete,
  onDeleteEdge,
}: {
  node: ErNode | null
  edge: ErEdge | null
  nodes: ErNode[]
  edges: ErEdge[]
  nameRef: RefObject<HTMLInputElement | null>
  onNode: (id: string, patch: Partial<ErNode>) => void
  onEdge: (id: string, patch: Partial<ErEdge>) => void
  onDelete: () => void
  onDeleteEdge: (id: string) => void
}) {
  const t = useT()
  const family = edge ? edgeFamily(edge, nodes) : "other"
  const links = node ? edges.filter((item) => item.source === node.id || item.target === node.id) : []
  return (
    <div className="erd-inspector">
      {node ? (
        <>
          <h2>{t(figureLabel(node.kind))}</h2>
          <label>
            {t("erdName")}
            <input
              ref={nameRef}
              value={node.label}
              maxLength={80}
              autoComplete="off"
              spellCheck={false}
              onChange={(event) => onNode(node.id, { label: event.target.value })}
            />
          </label>
          {node.kind === "attribute" ? (
            <label>
              {t("erdKey")}
              <select
                value={node.key}
                onChange={(event) => onNode(node.id, { key: event.target.value as ErNode["key"] })}
              >
                <option value="none">{t("erdKeyNone")}</option>
                <option value="primary">{t("erdKeyPrimary")}</option>
                <option value="partial">{t("erdKeyPartial")}</option>
              </select>
            </label>
          ) : null}
          {node.kind === "isa" ? (
            <label className="erd-check">
              <input
                type="checkbox"
                checked={node.disjoint}
                onChange={(event) => onNode(node.id, { disjoint: event.target.checked })}
              />
              {t("erdDisjoint")}
            </label>
          ) : null}
          {links.length > 0 ? (
            <>
              <h2>{t("erdGroupLines")}</h2>
              <ul className="erd-lines">
                {links.map((item) => (
                  <li key={item.id}>
                    <span>{otherEnd(item, node.id, nodes)}</span>
                    <button type="button" onClick={() => onDeleteEdge(item.id)}>
                      {t("erdDeleteLine")}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </>
      ) : null}
      {edge && family === "attribute" ? <p className="note">{t("erdAttributeLine")}</p> : null}
      {edge && family === "isa" ? (
        <label className="erd-check">
          <input
            type="checkbox"
            checked={edge.min === "1"}
            onChange={(event) => onEdge(edge.id, { min: event.target.checked ? "1" : "", max: "" })}
          />
          {t("erdTotalGeneralization")}
        </label>
      ) : null}
      {edge && family === "participation" ? (
        <>
          <h2>{t("erdGroupLines")}</h2>
          <div className="erd-presets">
            {(["0..1", "1..1", "0..n", "1..n"] as const).map((preset) => {
              const [min, max] = preset.split("..")
              return (
                <button key={preset} type="button" onClick={() => onEdge(edge.id, applyCardinality(edge, min, max))}>
                  {preset}
                </button>
              )
            })}
          </div>
          <div className="erd-pair">
            <label>
              {t("erdMin")}
              <input
                value={edge.min}
                maxLength={4}
                spellCheck={false}
                onChange={(event) => onEdge(edge.id, { min: event.target.value.slice(0, 4) })}
              />
            </label>
            <label>
              {t("erdMax")}
              <input
                value={edge.max}
                maxLength={4}
                spellCheck={false}
                onChange={(event) => onEdge(edge.id, { max: event.target.value.slice(0, 4) })}
              />
            </label>
          </div>
          <label className="erd-check">
            <input type="checkbox" checked={edge.one} onChange={(event) => onEdge(edge.id, { one: event.target.checked })} />
            {t("erdOneSide")}
          </label>
          <label>
            {t("erdRole")}
            <input
              value={edge.role}
              maxLength={40}
              autoComplete="off"
              spellCheck={false}
              onChange={(event) => onEdge(edge.id, { role: event.target.value })}
            />
          </label>
          <p className="note">{t("erdTotalNote")}</p>
        </>
      ) : null}
      {node || edge ? (
        <button className="danger" type="button" onClick={onDelete}>
          {edge ? t("erdDeleteLine") : t("erdDelete")}
        </button>
      ) : (
        <p className="note">{t("erdHow")}</p>
      )}
    </div>
  )
}

export function ErStudio({ account, onAccount }: { account: Account; onAccount: (account: Account) => void }) {
  const locale = useLocale()
  const t = useT()
  const [store, setStore] = useState<ErStore>(() => readStore() ?? emptyStore(translate(locale, "erdProjectDefault")))
  const [tool, setTool] = useState<Tool>("move")
  const [selected, setSelected] = useState<Selection | null>(null)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [cursor, setCursor] = useState<Point | null>(null)
  const [notice, setNotice] = useState("")
  const [panning, setPanning] = useState(false)
  const [confirm, setConfirm] = useState<"delete" | "example" | null>(null)
  const [ghost, setGhost] = useState<{ kind: NodeKind; x: number; y: number } | null>(null)
  const [camera, setCamera] = useState<Camera>({ cx: 560, cy: 340, scale: 1 })
  const [viewport, setViewport] = useState({ width: 960, height: 640 })
  const stageRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLDivElement>(null)
  const nameRef = useRef<HTMLInputElement>(null)
  const gestureRef = useRef<Gesture | null>(null)
  const chooseRef = useRef<(id: string) => void>(() => undefined)
  const pointRef = useRef<(clientX: number, clientY: number) => Point | null>(() => null)
  const cameraRef = useRef(camera)
  const toolRef = useRef(tool)
  const pendingRef = useRef(pendingId)

  const project = store.projects.find((item) => item.id === store.activeId) ?? store.projects[0]
  const view: View = viewFrom(camera, viewport.width, viewport.height)
  const viewRef = useRef(view)
  const projectRef = useRef(project)
  viewRef.current = view
  projectRef.current = project
  cameraRef.current = camera
  toolRef.current = tool
  pendingRef.current = pendingId

  function pointFromClient(clientX: number, clientY: number): Point | null {
    const canvas = canvasRef.current
    if (!canvas) return null
    const rect = canvas.getBoundingClientRect()
    if (rect.width < 1 || rect.height < 1) return null
    return clientToWorld(rect, viewRef.current, clientX, clientY)
  }
  pointRef.current = pointFromClient

  function updateProject(change: (current: ErProject) => ErProject) {
    setStore((current) => ({
      ...current,
      projects: current.projects.map((item) => (item.id === current.activeId ? change(item) : item)),
    }))
  }

  function fit(nodes: ErNode[]) {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    if (rect.width < 20 || rect.height < 20) return
    setCamera(cameraToFit(nodes, rect.width, rect.height))
  }

  chooseRef.current = (id: string) => {
    const toolNow = toolRef.current
    if (toolNow === "move") return
    const currentPending = pendingRef.current
    if (!currentPending) {
      setPendingId(id)
      return
    }
    if (currentPending === id) {
      setPendingId(null)
      setCursor(null)
      return
    }
    const result = connectPair(projectRef.current.nodes, projectRef.current.edges, currentPending, id, toolNow, {
      relationship: t("erdRelationship"),
      identifying: t("erdIdentifying"),
    })
    if (!result.ok) {
      setNotice(t(REASONS[result.reason]))
      return
    }
    updateProject((current) => ({ ...current, nodes: result.nodes, edges: result.edges }))
    setSelected(result.select)
    setPendingId(null)
    setCursor(null)
    setNotice("")
  }

  useEffect(() => {
    writeStore(store)
  }, [store])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(""), 4600)
    return () => window.clearTimeout(timer)
  }, [notice])

  useLayoutEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const measure = () => {
      const rect = canvas.getBoundingClientRect()
      const width = Math.max(1, Math.round(rect.width))
      const height = Math.max(1, Math.round(rect.height))
      setViewport((current) => (current.width === width && current.height === height ? current : { width, height }))
    }
    measure()
    if (projectRef.current.nodes.length > 0) {
      const rect = canvas.getBoundingClientRect()
      if (rect.width > 20 && rect.height > 20) setCamera(cameraToFit(projectRef.current.nodes, rect.width, rect.height))
    }
    const observer = new ResizeObserver(measure)
    observer.observe(canvas)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const onWheel = (event: WheelEvent) => {
      event.preventDefault()
      const rect = canvas.getBoundingClientRect()
      const factor = event.deltaY < 0 ? 1.08 : 1 / 1.08
      setCamera((current) => zoomAt(current, rect, event.clientX, event.clientY, factor))
    }
    canvas.addEventListener("wheel", onWheel, { passive: false })
    return () => canvas.removeEventListener("wheel", onWheel)
  }, [])

  useEffect(() => {
    function onMove(event: PointerEvent) {
      const gesture = gestureRef.current
      if (gesture && event.pointerId === gesture.pointerId) {
        if (gesture.type === "pan") {
          const dx = (event.clientX - gesture.x) / gesture.scale
          const dy = (event.clientY - gesture.y) / gesture.scale
          setCamera((current) => ({ ...current, cx: gesture.cx - dx, cy: gesture.cy - dy }))
          return
        }
        if (!gesture.moved && Math.hypot(event.clientX - gesture.startX, event.clientY - gesture.startY) < 3) return
        gesture.moved = true
        const world = pointRef.current(event.clientX, event.clientY)
        if (!world) return
        const x = snap(world.x - gesture.ox)
        const y = snap(world.y - gesture.oy)
        const nodeId = gesture.id
        setStore((current) => ({
          ...current,
          projects: current.projects.map((item) =>
            item.id !== current.activeId
              ? item
              : { ...item, nodes: item.nodes.map((node) => (node.id === nodeId ? { ...node, x, y } : node)) },
          ),
        }))
        return
      }
      if (pendingRef.current) {
        const world = pointRef.current(event.clientX, event.clientY)
        if (world) setCursor(world)
      }
    }
    function onUp(event: PointerEvent) {
      const gesture = gestureRef.current
      if (!gesture || event.pointerId !== gesture.pointerId) return
      gestureRef.current = null
      setPanning(false)
    }
    window.addEventListener("pointermove", onMove)
    window.addEventListener("pointerup", onUp)
    return () => {
      window.removeEventListener("pointermove", onMove)
      window.removeEventListener("pointerup", onUp)
    }
  }, [])

  function place(kind: NodeKind, x: number, y: number) {
    const node = createNode(kind, x, y, kind === "isa" ? "ISA" : t(figureLabel(kind)))
    updateProject((current) => ({ ...current, nodes: [...current.nodes, node] }))
    setSelected({ type: "node", id: node.id })
    setPendingId(null)
    setCursor(null)
  }

  function onFigurePointerDown(event: ReactPointerEvent<HTMLButtonElement>, kind: NodeKind) {
    if (event.button !== 0) return
    event.preventDefault()
    const pointerId = event.pointerId
    const startX = event.clientX
    const startY = event.clientY
    let dragging = false
    const move = (ev: PointerEvent) => {
      if (ev.pointerId !== pointerId) return
      if (!dragging && Math.hypot(ev.clientX - startX, ev.clientY - startY) < 4) return
      dragging = true
      setGhost({ kind, x: ev.clientX, y: ev.clientY })
    }
    const up = (ev: PointerEvent) => {
      if (ev.pointerId !== pointerId) return
      window.removeEventListener("pointermove", move)
      window.removeEventListener("pointerup", up)
      setGhost(null)
      if (!dragging) {
        const current = viewRef.current
        const stagger = (projectRef.current.nodes.length % 6) * 18
        place(kind, current.x + current.w / 2 + stagger, current.y + current.h / 2 + stagger)
        return
      }
      const canvas = canvasRef.current
      if (!canvas) return
      const rect = canvas.getBoundingClientRect()
      const inside = ev.clientX >= rect.left && ev.clientX <= rect.right && ev.clientY >= rect.top && ev.clientY <= rect.bottom
      if (!inside) return
      const world = clientToWorld(rect, viewRef.current, ev.clientX, ev.clientY)
      place(kind, world.x, world.y)
    }
    window.addEventListener("pointermove", move)
    window.addEventListener("pointerup", up)
  }

  function onNodePointerDown(event: ReactPointerEvent, id: string) {
    if (event.button !== 0) return
    event.stopPropagation()
    event.preventDefault()
    stageRef.current?.focus()
    setSelected({ type: "node", id })
    if (toolRef.current !== "move") {
      chooseRef.current(id)
      return
    }
    const world = pointRef.current(event.clientX, event.clientY)
    const node = projectRef.current.nodes.find((item) => item.id === id)
    if (!world || !node) return
    gestureRef.current = {
      type: "node",
      pointerId: event.pointerId,
      id,
      ox: world.x - node.x,
      oy: world.y - node.y,
      moved: false,
      startX: event.clientX,
      startY: event.clientY,
    }
  }

  function onEdgePointerDown(event: ReactPointerEvent, id: string) {
    if (event.button !== 0) return
    event.stopPropagation()
    event.preventDefault()
    stageRef.current?.focus()
    setSelected({ type: "edge", id })
    setPendingId(null)
    setCursor(null)
  }

  function onBackgroundPointerDown(event: ReactPointerEvent) {
    if (event.button !== 0) return
    event.preventDefault()
    stageRef.current?.focus()
    setSelected(null)
    if (toolRef.current !== "move") {
      setPendingId(null)
      setCursor(null)
      return
    }
    const current = cameraRef.current
    setPanning(true)
    gestureRef.current = {
      type: "pan",
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      cx: current.cx,
      cy: current.cy,
      scale: current.scale,
    }
  }

  function deleteEdge(id: string) {
    updateProject((current) => ({ ...current, edges: current.edges.filter((edge) => edge.id !== id) }))
    setSelected((current) => (current?.type === "edge" && current.id === id ? null : current))
    setPendingId(null)
    setCursor(null)
  }

  function removeSelected() {
    if (!selected) return
    if (selected.type === "node") {
      const id = selected.id
      updateProject((current) => ({ ...current, ...removeNode(current.nodes, current.edges, id) }))
      setSelected(null)
      setPendingId(null)
      setCursor(null)
      return
    }
    deleteEdge(selected.id)
  }

  function onKeyDown(event: React.KeyboardEvent) {
    const target = event.target
    if (target instanceof HTMLElement && target.closest("input, textarea, select")) return
    if (event.key === "Escape") {
      setPendingId(null)
      setCursor(null)
      setNotice("")
      setConfirm(null)
      if (tool !== "move") setTool("move")
      else setSelected(null)
      return
    }
    if ((event.key === "Delete" || event.key === "Backspace") && selected) {
      event.preventDefault()
      removeSelected()
    }
  }

  function loadExample() {
    const sample = accidentExample()
    updateProject((current) => ({ ...current, nodes: sample.nodes, edges: sample.edges }))
    setConfirm(null)
    setSelected(null)
    setPendingId(null)
    setCursor(null)
    setNotice("")
    requestAnimationFrame(() => fit(sample.nodes))
  }

  function deleteActive() {
    const base = t("erdProjectDefault")
    setStore((current) => {
      const remaining = current.projects.filter((item) => item.id !== current.activeId)
      if (remaining.length === 0) {
        const fresh = createEmpty(base)
        return { activeId: fresh.id, projects: [fresh] }
      }
      return { activeId: remaining[0].id, projects: remaining }
    })
    setConfirm(null)
    setSelected(null)
    setPendingId(null)
    setCursor(null)
    setNotice("")
  }

  const selectedNode = selected?.type === "node" ? project.nodes.find((node) => node.id === selected.id) ?? null : null
  const selectedEdge = selected?.type === "edge" ? project.edges.find((edge) => edge.id === selected.id) ?? null : null
  const linking = tool !== "move"
  const status =
    notice ||
    (tool === "many-one" && pendingId ? t("erdLinkManyOne") : "") ||
    (linking && pendingId ? t("erdLinkSecond") : "") ||
    (linking ? t("erdLinkFirst") : "")
  const mode = panning ? "is-panning" : tool === "move" ? "is-move" : "is-link"

  return (
    <div className="shell erd-shell" ref={stageRef} tabIndex={-1} onKeyDown={onKeyDown}>
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1>
            <Logo />
          </h1>
          <AccountIdentity account={account} onAccount={onAccount} stats="days" />
        </div>
        <div className="erd-project">
          <input
            aria-label={t("erdProject")}
            value={project.name}
            maxLength={80}
            spellCheck={false}
            onChange={(event) => updateProject((current) => ({ ...current, name: event.target.value }))}
            onBlur={(event) => {
              if (!event.target.value.trim()) updateProject((current) => ({ ...current, name: t("erdProjectDefault") }))
            }}
          />
          {store.projects.length > 1 ? (
            <select
              aria-label={t("erdProject")}
              value={project.id}
              onChange={(event) => {
                const next = store.projects.find((item) => item.id === event.target.value)
                setStore((current) => ({ ...current, activeId: event.target.value }))
                setSelected(null)
                setPendingId(null)
                setCursor(null)
                setTool("move")
                if (next) requestAnimationFrame(() => fit(next.nodes))
              }}
            >
              {store.projects.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name || t("erdProjectDefault")}
                </option>
              ))}
            </select>
          ) : null}
          {confirm ? (
            <div className="erd-confirm">
              <span>{confirm === "delete" ? t("erdConfirmDelete") : t("erdConfirmExample")}</span>
              <button type="button" className="primary" onClick={confirm === "delete" ? deleteActive : loadExample}>
                {confirm === "delete" ? t("erdDelete") : t("erdExample")}
              </button>
              <button type="button" className="top-action" onClick={() => setConfirm(null)}>
                {t("erdCancel")}
              </button>
            </div>
          ) : (
            <>
              <button
                type="button"
                className="top-action"
                onClick={() => {
                  const created = createEmpty(nextName(store.projects, t("erdProjectDefault")))
                  setStore((current) => ({ activeId: created.id, projects: [...current.projects, created] }))
                  setSelected(null)
                  setPendingId(null)
                  setCursor(null)
                  setTool("move")
                  setNotice("")
                }}
              >
                {t("erdNewProject")}
              </button>
              <button
                type="button"
                className="top-action"
                onClick={() => {
                  if (project.nodes.length === 0) loadExample()
                  else setConfirm("example")
                }}
              >
                {t("erdExample")}
              </button>
              <button type="button" className="top-action" onClick={() => setConfirm("delete")}>
                {t("erdDeleteProject")}
              </button>
            </>
          )}
        </div>
        <div className="actions">
          <LeaveSubjectButton />
        </div>
      </header>
      <div className="erd-body">
        <div className={`erd-canvas-wrap ${mode}`}>
          <div className="erd-zoom">
            <button type="button" aria-label={t("erdZoomIn")} onClick={() => setCamera((current) => ({ ...current, scale: clampScale(current.scale * 1.12) }))}>
              +
            </button>
            <button type="button" aria-label={t("erdZoomOut")} onClick={() => setCamera((current) => ({ ...current, scale: clampScale(current.scale / 1.12) }))}>
              −
            </button>
            <button type="button" aria-label={t("erdFit")} onClick={() => fit(project.nodes)}>
              <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
                <path d="M2 5V2h3M9 2h3v3M12 9v3H9M5 12H2V9" fill="none" stroke="currentColor" strokeWidth="1.4" />
              </svg>
            </button>
          </div>
          <div className="erd-canvas-host" ref={canvasRef}>
            <ErCanvas
              nodes={project.nodes}
              edges={project.edges}
              view={view}
              selectedId={selected?.id ?? null}
              pendingId={pendingId}
              cursor={cursor}
              emptyLabel={t("erdEmpty")}
              canvasLabel={t("erdCanvas")}
              disjointLabel={t("erdDisjointWord")}
              deleteLineLabel={t("erdDeleteLine")}
              onBackgroundPointerDown={onBackgroundPointerDown}
              onNodePointerDown={onNodePointerDown}
              onNodeDoubleClick={(id) => {
                setSelected({ type: "node", id })
                setTool("move")
                setPendingId(null)
                requestAnimationFrame(() => nameRef.current?.focus())
              }}
              onEdgePointerDown={onEdgePointerDown}
              onDeleteEdge={deleteEdge}
            />
          </div>
          {status ? <p className={notice ? "erd-status is-error" : "erd-status"} role="status">{status}</p> : null}
        </div>
        <aside className="erd-palette" aria-label={t("erdPalette")}>
          <div className="erd-palette-scroll">
            <p className="note">{t("erdSavedLocal")}</p>
            <section>
              <h2>{t("erdGroupLines")}</h2>
              <div className="erd-tools">
                {TOOLS.map((item) => (
                  <button
                    key={item}
                    type="button"
                    className="erd-tool"
                    aria-pressed={tool === item}
                    onClick={() => {
                      setTool(item)
                      setPendingId(null)
                      setCursor(null)
                    }}
                  >
                    <LineIcon tool={item} />
                    {t(toolLabel(item))}
                  </button>
                ))}
              </div>
            </section>
            <section>
              <h2>{t("erdGroupFigures")}</h2>
              <div className="erd-figures">
                {FIGURES.map((kind) => (
                  <button key={kind} type="button" className="erd-figure" onPointerDown={(event) => onFigurePointerDown(event, kind)}>
                    <Glyph kind={kind} />
                    {t(figureLabel(kind))}
                  </button>
                ))}
              </div>
            </section>
            <p className="note">{t("erdStandard")}</p>
          </div>
          <Inspector
            node={selectedNode}
            edge={selectedEdge}
            nodes={project.nodes}
            edges={project.edges}
            nameRef={nameRef}
            onNode={(id, patch) => updateProject((current) => ({
              ...current,
              nodes: current.nodes.map((node) => (node.id === id ? { ...node, ...patch } : node)),
            }))}
            onEdge={(id, patch) => updateProject((current) => ({
              ...current,
              edges: current.edges.map((edge) => (edge.id === id ? { ...edge, ...patch } : edge)),
            }))}
            onDelete={removeSelected}
            onDeleteEdge={deleteEdge}
          />
        </aside>
      </div>
      {ghost ? (
        <div className="erd-ghost" style={{ left: ghost.x, top: ghost.y }}>
          <Glyph kind={ghost.kind} />
        </div>
      ) : null}
    </div>
  )
}
