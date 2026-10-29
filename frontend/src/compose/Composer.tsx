import { useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent, type PointerEvent as ReactPointerEvent } from "react"

import { api, type Account, type Algorithm, type Project } from "../api"
import { allKeywordDisplays, spellText } from "../dialect"
import { useLocale, useT, type MessageKey } from "../i18n"
import { pasteBlockedFor, refusePaste } from "../paste"
import { saveDownload } from "../saveFile"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { LeaveSubjectButton } from "../subjects/leave"
import { highlightSource } from "../editor/highlight"
import { labelAnchor } from "../diagram/figures"
import { ShapeGlyph, SwitchGlyph } from "../diagram/glyphs"
import { keywordSet } from "../words"
import { NsIcon, Structogram } from "./Structogram"
import { importSource } from "./import"
import { layoutProgram } from "./layout"
import {
  TYPE_OPTIONS,
  addCase,
  addRoutine,
  algorithmName,
  createRoutine,
  createStep,
  emptyProgram,
  figureForKind,
  findRoutine,
  findStep,
  guessingGame,
  insertStep,
  isRoutineKind,
  isStepKind,
  issues,
  moveStep,
  parseProgram,
  removeCase,
  removeRoutine,
  removeStep,
  toSource,
  updateRoutine,
  updateStep,
  type Program,
  type Routine,
  type RoutineKind,
  type SlotPath,
  type Step,
  type StepKind,
} from "./model"
import "./composer.css"

const STORAGE = "traza.composer.v1"
const NS_STORAGE = "traza.composer.ns.v1"
const NARROW = "(max-width: 820px)"
const SIDE_MIN = 200
const CODE_MIN = 220
const CANVAS_MIN = 160
const CODE_ROW_MIN = 140

function clampPane(value: number, min: number, max: number): number {
  return Math.round(Math.min(Math.max(value, min), Math.max(min, max)))
}

type PaletteKind = StepKind | RoutineKind

const FIGURE_BLOCKS: Record<string, string[]> = {
  definir: ["traza_definir"],
  dimension: ["traza_dimension"],
  asignar: ["traza_asignar"],
  leer: ["traza_leer"],
  escribir: ["traza_escribir"],
  si: ["traza_si", "traza_si_sino"],
  mientras: ["traza_mientras"],
  repetir: ["traza_repetir"],
  para: ["traza_para"],
  segun: ["traza_segun"],
  funcion: ["traza_funcion"],
  procedimiento: ["traza_procedimiento"],
  borrar: ["traza_borrar_pantalla"],
  esperar: ["traza_esperar"],
  comentario: ["traza_comentario"],
}

const PALETTE: { kind: PaletteKind; title: MessageKey; hint: MessageKey; nsTitle?: MessageKey }[] = [
  { kind: "definir", title: "figDefine", hint: "hintDeclare" },
  { kind: "dimension", title: "figDimension", hint: "hintArray" },
  { kind: "asignar", title: "figAssign", hint: "hintProcess" },
  { kind: "leer", title: "figRead", hint: "hintInput" },
  { kind: "escribir", title: "figWrite", hint: "hintOutput" },
  { kind: "si", title: "figIf", hint: "hintDecision" },
  { kind: "mientras", title: "figWhile", hint: "hintLoop" },
  { kind: "repetir", title: "figRepeat", nsTitle: "figUntil", hint: "hintLoop" },
  { kind: "para", title: "figFor", hint: "hintCounted" },
  { kind: "segun", title: "figSwitch", hint: "hintCases" },
  { kind: "funcion", title: "figFunction", hint: "hintOutside" },
  { kind: "procedimiento", title: "figProcedure", hint: "hintOutside" },
  { kind: "borrar", title: "figClear", hint: "hintProcess" },
  { kind: "esperar", title: "figWait", hint: "hintProcess" },
  { kind: "comentario", title: "figComment", hint: "hintComment" },
]

const NS_ORDER: PaletteKind[] = [
  "comentario",
  "asignar",
  "escribir",
  "leer",
  "si",
  "segun",
  "mientras",
  "repetir",
  "para",
  "definir",
  "dimension",
  "borrar",
  "esperar",
  "funcion",
  "procedimiento",
]

const KNOWN: Record<string, MessageKey> = {
  "El nombre del algoritmo tiene que ser un identificador.": "badAlgorithmName",
  "Falta una condición.": "missingCondition",
  "Falta el nombre en Definir.": "missingDefine",
  "Falta el nombre o el tamaño en Dimension.": "missingDimension",
  "Falta completar una asignación.": "missingAssign",
  "Hay una figura sin texto.": "emptyFigure",
  "Falta completar un Para.": "missingFor",
  "Falta la expresión del Según.": "missingSwitch",
  "Hay un caso del Según sin etiqueta.": "emptyCase",
  "El nombre de la función no es válido.": "badFunction",
  "El nombre del procedimiento no es válido.": "badProcedure",
  "Falta el resultado de la función.": "missingResult",
  "Se usó el primer algoritmo del archivo.": "importFirst",
  "Falta cerrar el comentario.": "importComment",
  "Falta cerrar un texto.": "importString",
  "El texto no tiene un bloque Algoritmo.": "importNoAlgorithm",
  "Falta el nombre del algoritmo.": "importNoName",
  "Falta el tipo después de Como.": "importNoType",
  "Falta el texto de la instrucción.": "importNoText",
  "Falta el tiempo de Esperar.": "importNoWait",
  "Falta la condición del Si.": "importNoIf",
  "Falta la condición del Mientras.": "importNoWhile",
  "Falta la condición del Repetir.": "importNoRepeat",
  "Falta la variable del Para.": "importNoForVar",
  "Falta la etiqueta de un caso del Según.": "importNoCase",
  "Falta FinAlgoritmo.": "importNoEnd",
  "No se pudo leer el algoritmo.": "readAlgorithmError",
  "No se pudieron cargar los proyectos.": "projectsLoadError",
  "No se pudieron cargar los algoritmos.": "algorithmsLoadError",
  "Escribe el nombre del algoritmo.": "writeAlgorithmName",
  "Escribe el nombre del proyecto.": "writeProjectName",
  "Elige un proyecto.": "pickProject",
  "No se pudo guardar el algoritmo.": "saveAlgorithmError",
}

function loadProgram(storage: string): Program {
  try {
    const raw = localStorage.getItem(storage)
    if (!raw) return emptyProgram()
    return parseProgram(JSON.parse(raw) as unknown) ?? emptyProgram()
  } catch {
    return emptyProgram()
  }
}

function slotHint(path: SlotPath, moving: boolean, t: (key: MessageKey) => string): string {
  if (moving) {
    if (path.scope === "then") return t("moveTrue")
    if (path.scope === "else") return t("moveFalse")
    if (path.scope === "body") return t("moveLoop")
    if (path.scope === "case") return t("moveCase")
    if (path.scope === "routine") return t("moveRoutine")
    if (path.scope === "other") return t("moveOther")
    return t("moveHere")
  }
  if (path.scope === "then") return t("dropTrue")
  if (path.scope === "else") return t("dropFalse")
  if (path.scope === "body") return t("dropLoop")
  if (path.scope === "case") return t("dropCase")
  if (path.scope === "routine") return t("dropRoutine")
  if (path.scope === "other") return t("dropOther")
  return t("dropFlow")
}

function shown(text: string, t: (key: MessageKey, vars?: Record<string, string | number>) => string): string {
  const built = /^Diagrama armado desde «(.+)»\.$/.exec(text)
  if (built) return t("builtFrom", { name: built[1] })
  const exists = /^Ya existe «(.+)»\. Confirma si quieres reemplazar su código\.$/.exec(text)
  if (exists) return t("replaceExists", { name: exists[1] })
  const key = KNOWN[text]
  return key ? t(key) : text
}

export type DiagramRequest = { name?: string; source?: string; semicolons: boolean; token: number }

export function Composer({
  account = null,
  onAccount,
  active,
  incoming,
  onBack,
  onOpenInEditor,
  embedded = false,
  isolated = false,
  allowedBlocks = null,
  onSource,
  preview = false,
  pasteBlocked = false,
  variant = "flow",
}: {
  account?: Account | null
  onAccount?: (account: Account) => void
  active: boolean
  incoming: DiagramRequest | null
  onBack: () => void
  onOpenInEditor: (target: { projectId: string; algorithmId: string }) => void
  embedded?: boolean
  isolated?: boolean
  allowedBlocks?: readonly string[] | null
  onSource?: (source: string) => void
  preview?: boolean
  pasteBlocked?: boolean
  variant?: "flow" | "ns"
}) {
  const t = useT()
  const locale = useLocale()
  const nassi = variant === "ns"
  const storage = nassi ? NS_STORAGE : STORAGE
  const blocked = pasteBlocked || (account != null && pasteBlockedFor(account))
  const [program, setProgram] = useState<Program>(() => (isolated ? emptyProgram() : loadProgram(storage)))
  const [selected, setSelected] = useState<string | null>(null)
  const [armed, setArmed] = useState<PaletteKind | null>(null)
  const [hot, setHot] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [copied, setCopied] = useState(false)
  const [importNotes, setImportNotes] = useState<string[]>([])
  const [importError, setImportError] = useState("")
  const [sendOpen, setSendOpen] = useState(false)
  const [semicolons, setSemicolons] = useState(true)
  const [passedName, setPassedName] = useState<string | null>(null)
  const [sideWidth, setSideWidth] = useState(280)
  const [codeWidth, setCodeWidth] = useState(340)
  const [codeHeight, setCodeHeight] = useState(240)
  const [stacked, setStacked] = useState(() => window.matchMedia(NARROW).matches)
  const [sheet, setSheet] = useState({ width: 584, height: 180 })
  const sheetRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const frameRef = useRef<HTMLDivElement>(null)
  const reserved = useMemo(() => keywordSet(allKeywordDisplays()), [])

  const palette = useMemo(() => {
    const permit = allowedBlocks && allowedBlocks.length > 0 ? new Set(allowedBlocks) : null
    const source = permit ? PALETTE.filter((item) => (FIGURE_BLOCKS[item.kind] ?? []).some((block) => permit.has(block))) : PALETTE
    if (!nassi) return source
    const rank = new Map(NS_ORDER.map((kind, index) => [kind, index]))
    return [...source].sort((left, right) => (rank.get(left.kind) ?? 99) - (rank.get(right.kind) ?? 99))
  }, [allowedBlocks, nassi])
  const placing = Boolean(armed) || dragging
  const scene = useMemo(() => layoutProgram(program, locale, placing), [program, locale, placing])
  const source = useMemo(() => toSource(program, semicolons, locale), [program, semicolons, locale])
  const reportSource = useRef(onSource)
  reportSource.current = onSource
  const notes = useMemo(() => issues(program), [program])
  const colored = useMemo(() => highlightSource(source.endsWith("\n") ? source.slice(0, -1) : source, reserved), [source, reserved])
  const current = selected ? findStep(program, selected) : null
  const routine = selected ? findRoutine(program, selected) : null
  const shapeKey = scene.nodes.map((node) => node.id).join("|")

  useEffect(() => {
    if (!nassi) return
    const node = sheetRef.current
    if (!node) return
    const update = () => {
      const width = Math.max(1, node.offsetWidth)
      const height = Math.max(1, node.offsetHeight)
      setSheet((current) => (current.width === width && current.height === height ? current : { width, height }))
    }
    update()
    const observer = new ResizeObserver(update)
    observer.observe(node)
    return () => observer.disconnect()
  }, [nassi, source])

  useEffect(() => {
    if (nassi) return
    const scroller = scrollRef.current
    const start = scene.nodes.find((node) => node.id === "start")
    if (!scroller || !start) return
    const frame = window.requestAnimationFrame(() => {
      const center = (start.x + start.width / 2) * zoom
      scroller.scrollLeft = Math.max(0, center - scroller.clientWidth / 2)
      scroller.scrollTop = 0
    })
    return () => window.cancelAnimationFrame(frame)
  }, [nassi, shapeKey, zoom])

  useEffect(() => {
    reportSource.current?.(source)
  }, [source])

  useEffect(() => {
    if (isolated) return
    localStorage.setItem(storage, JSON.stringify(program))
  }, [isolated, program, storage])

  useEffect(() => {
    const end = () => {
      setDragging(false)
      setHot(null)
    }
    window.addEventListener("dragend", end)
    return () => window.removeEventListener("dragend", end)
  }, [])

  useEffect(() => {
    const media = window.matchMedia(NARROW)
    const apply = () => setStacked(media.matches)
    apply()
    media.addEventListener("change", apply)
    return () => media.removeEventListener("change", apply)
  }, [])

  useEffect(() => {
    if (!active) return
    const fit = () => {
      const box = frameRef.current?.getBoundingClientRect()
      if (!box || box.width < 100) return
      const narrow = window.matchMedia(NARROW).matches
      setSideWidth((value) => clampPane(value, SIDE_MIN, box.width - (narrow ? 6 : 12 + CODE_MIN) - CANVAS_MIN))
      if (narrow) setCodeHeight((value) => clampPane(value, CODE_ROW_MIN, box.height - 160))
      else setCodeWidth((value) => clampPane(value, CODE_MIN, box.width - SIDE_MIN - 12 - CANVAS_MIN))
    }
    fit()
    window.addEventListener("resize", fit)
    return () => window.removeEventListener("resize", fit)
  }, [active])

  useEffect(() => {
    if (!incoming) return
    setSemicolons(incoming.semicolons)
    if (incoming.name != null) setPassedName(incoming.name)
    if (incoming.source == null || incoming.name == null) return
    try {
      const result = importSource(incoming.source)
      setProgram(result.program)
      setImportNotes([`Diagrama armado desde «${incoming.name}».`, ...result.notes])
      setImportError("")
      setSelected(null)
      setArmed(null)
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "No se pudo leer el algoritmo."
      setImportError(message)
    }
  }, [incoming])

  useEffect(() => {
    if (!active || preview) return
    const onKey = (event: KeyboardEvent) => {
      if (sendOpen) return
      if (event.key !== "Delete" && event.key !== "Backspace") return
      const target = event.target
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) return
      if (!selected) return
      event.preventDefault()
      setProgram((value) => (value.routines.some((item) => item.id === selected) ? removeRoutine(value, selected) : removeStep(value, selected)))
      setSelected(null)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [active, preview, selected, sendOpen])

  function place(path: SlotPath, data: string) {
    if (data.startsWith("piece:")) {
      const kind = data.slice(6)
      if (isRoutineKind(kind)) {
        const routine = createRoutine(kind)
        setProgram((value) => addRoutine(value, routine))
        setSelected(routine.id)
        setArmed(null)
        return
      }
      if (!isStepKind(kind)) return
      const step = createStep(kind)
      setProgram((value) => insertStep(value, path, step))
      setSelected(step.id)
      setArmed(null)
      return
    }
    if (data.startsWith("move:")) {
      const id = data.slice(5)
      setProgram((value) => moveStep(value, id, path))
      setSelected(id)
      setArmed(null)
    }
  }

  function append(kind: PaletteKind) {
    if (isRoutineKind(kind)) {
      const routine = createRoutine(kind)
      setProgram((value) => addRoutine(value, routine))
      setSelected(routine.id)
      setArmed(null)
      return
    }
    const step = createStep(kind)
    setProgram((value) => insertStep(value, { scope: "root", index: value.body.length }, step))
    setSelected(step.id)
    setArmed(null)
  }

  async function copySource() {
    try {
      await navigator.clipboard.writeText(source)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  function sideLimit() {
    const box = frameRef.current?.getBoundingClientRect()
    const reserved = stacked ? 6 + CANVAS_MIN : 12 + codeWidth + CANVAS_MIN
    const max = box ? box.width - reserved : 480
    return { min: SIDE_MIN, max: Math.max(SIDE_MIN, Math.round(max)) }
  }

  function codeLimit() {
    const box = frameRef.current?.getBoundingClientRect()
    if (stacked) {
      const max = box ? box.height - 160 : 480
      return { min: CODE_ROW_MIN, max: Math.max(CODE_ROW_MIN, Math.round(max)) }
    }
    const max = box ? box.width - sideWidth - 12 - CANVAS_MIN : 640
    return { min: CODE_MIN, max: Math.max(CODE_MIN, Math.round(max)) }
  }

  function resizeSide(next: number) {
    const { min, max } = sideLimit()
    setSideWidth(clampPane(next, min, max))
  }

  function resizeCode(next: number) {
    const { min, max } = codeLimit()
    if (stacked) setCodeHeight(clampPane(next, min, max))
    else setCodeWidth(clampPane(next, min, max))
  }

  function dragPane(event: ReactPointerEvent<HTMLButtonElement>, cursor: string, onMove: (ev: PointerEvent) => void) {
    const frame = frameRef.current
    if (!frame) return
    event.preventDefault()
    const handle = event.currentTarget
    try {
      handle.setPointerCapture(event.pointerId)
    } catch {
      /* El arrastre sigue por los eventos del propio separador. */
    }
    const body = document.body
    const previousCursor = body.style.cursor
    const previousSelect = body.style.userSelect
    body.style.cursor = cursor
    body.style.userSelect = "none"
    const stop = () => {
      handle.removeEventListener("pointermove", onMove)
      handle.removeEventListener("pointerup", stop)
      handle.removeEventListener("pointercancel", stop)
      body.style.cursor = previousCursor
      body.style.userSelect = previousSelect
    }
    handle.addEventListener("pointermove", onMove)
    handle.addEventListener("pointerup", stop)
    handle.addEventListener("pointercancel", stop)
  }

  function downloadSource() {
    void saveDownload(
      `${algorithmName(program.name)}.txt`,
      new Blob([source], { type: "text/plain;charset=utf-8" }),
    )
  }

  return (
    <div
      className={["shell composer-shell", embedded ? "composer-embedded" : "", preview ? "composer-preview" : ""].filter(Boolean).join(" ")}
      onPaste={blocked ? refusePaste : undefined}
      onDrop={blocked ? refusePaste : undefined}
    >
      <header className="topbar topbar-editor">
        <div className="brand">
          {embedded ? null : <h1><Logo mark />{t(nassi ? "composeNs" : "composeTitle")}</h1>}
          {embedded || !account ? null : <AccountIdentity account={account} onAccount={onAccount} />}
          <label className="composer-name">
            {t("algorithm")}
            <input
              aria-label={t("algorithmName")}
              value={program.name}
              onChange={(event) => setProgram((value) => ({ ...value, name: event.target.value }))}
            />
          </label>
        </div>
        <div className="actions">
          {embedded ? null : <LeaveSubjectButton />}
          {embedded ? null : (
            <button
              type="button"
              className="top-action"
              onClick={() => {
                setProgram(guessingGame())
                setPassedName(null)
                setSelected(null)
                setImportNotes([])
                setImportError("")
              }}
            >
              {t("loadExample")}
            </button>
          )}
          <button
            type="button"
            className="top-action"
            onClick={() => {
              setProgram(emptyProgram())
              setPassedName(null)
              setSelected(null)
              setImportNotes([])
              setImportError("")
            }}
          >
            {t("clearDiagram")}
          </button>
          {embedded ? null : (
            <button type="button" className="top-action" onClick={() => setSendOpen(true)}>
              {t("sendToEditor")}
            </button>
          )}
          {embedded ? null : (
            <button type="button" className="top-leave" onClick={onBack}>
              {t("backToEditor")}
            </button>
          )}
        </div>
      </header>
      <div
        className={`composer${dragging ? " is-dragging" : ""}${armed ? " is-placing" : ""}`}
        ref={frameRef}
        style={{ "--side-width": `${sideWidth}px`, "--code-width": `${codeWidth}px`, "--code-height": `${codeHeight}px` } as CSSProperties}
      >
        <aside className="composer-side">
          <Inspector
            step={current}
            routine={routine}
            onChange={(recipe) => {
              if (!current) return
              setProgram((value) => updateStep(value, current.id, recipe))
            }}
            onChangeRoutine={(recipe) => {
              if (!routine) return
              setProgram((value) => updateRoutine(value, routine.id, recipe))
            }}
            onAddCase={() => current && setProgram((value) => addCase(value, current.id))}
            onRemoveCase={() => current && setProgram((value) => removeCase(value, current.id))}
            onRemove={() => {
              if (routine) {
                setProgram((value) => removeRoutine(value, routine.id))
                setSelected(null)
                return
              }
              if (!current) return
              setProgram((value) => removeStep(value, current.id))
              setSelected(null)
            }}
          />
          <div className="composer-block composer-palette">
            <h2>{t("figures")}</h2>
            <p className="note">{nassi ? t("figuresNoteNs") : t("figuresNote")}</p>
            <div className="palette">
              {palette.map((item) => {
                const figure = item.kind === "funcion" || item.kind === "procedimiento" ? "subprocess" : figureForKind(item.kind)
                return (
                  <button
                    key={item.kind}
                    type="button"
                    className={armed === item.kind ? "palette-item armed" : "palette-item"}
                    draggable
                    aria-pressed={armed === item.kind}
                    onClick={() => setArmed((value) => (value === item.kind ? null : item.kind))}
                    onDoubleClick={() => append(item.kind)}
                    onDragStart={(event) => {
                      event.dataTransfer.setData("text/plain", `piece:${item.kind}`)
                      event.dataTransfer.effectAllowed = "copy"
                      setDragging(true)
                      setArmed(item.kind)
                    }}
                  >
                    <span className="palette-glyph" aria-hidden="true">
                      {nassi ? (
                        <NsIcon kind={item.kind} locale={locale} />
                      ) : figure === "switch" ? (
                        <span className="shape shape-switch">
                          <SwitchGlyph width={120} height={64} cases={[{ label: "1", width: 60 }, { label: null, width: 60 }]} />
                        </span>
                      ) : (
                        <span className={`shape shape-${figure}`}>
                          <ShapeGlyph figure={figure} />
                        </span>
                      )}
                    </span>
                    <span>
                      <strong>{t(nassi && item.nsTitle ? item.nsTitle : item.title)}</strong>
                      <small>{t(item.hint)}</small>
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        </aside>
        <button
          type="button"
          className="splitter"
          role="separator"
          aria-orientation="vertical"
          aria-label={t("adjustFigures")}
          aria-valuenow={sideWidth}
          aria-valuemin={sideLimit().min}
          aria-valuemax={sideLimit().max}
          onPointerDown={(event) => {
            dragPane(event, "col-resize", (ev) => {
              const box = frameRef.current?.getBoundingClientRect()
              if (box) resizeSide(ev.clientX - box.left)
            })
          }}
          onKeyDown={(event) => {
            const step = event.shiftKey ? 48 : 16
            if (event.key === "ArrowRight") {
              event.preventDefault()
              resizeSide(sideWidth + step)
            }
            if (event.key === "ArrowLeft") {
              event.preventDefault()
              resizeSide(sideWidth - step)
            }
          }}
        />
        <div className="composer-canvas">
          <div className="composer-zoom">
            <div className="composer-zoom-controls">
              <button type="button" onClick={() => setZoom((value) => Math.max(0.45, Math.round((value - 0.1) * 10) / 10))}>
                −
              </button>
              <button type="button" onClick={() => setZoom(1)}>
                {Math.round(zoom * 100)}%
              </button>
              <button type="button" onClick={() => setZoom((value) => Math.min(1.6, Math.round((value + 0.1) * 10) / 10))}>
                +
              </button>
            </div>
          </div>
          <div className="composer-scroll" ref={scrollRef}>
            {nassi ? (
              <div className="composer-stage" style={{ width: sheet.width * zoom, height: sheet.height * zoom }}>
                <div
                  className="composer-scene"
                  style={{ width: sheet.width, height: sheet.height, transform: `scale(${zoom})` }}
                  onClick={() => setSelected(null)}
                >
                  <div className="ns-sheet" ref={sheetRef}>
                    <Structogram
                      program={program}
                      locale={locale}
                      selected={selected}
                      armed={armed}
                      preview={preview}
                      dragging={dragging}
                      hot={hot}
                      hint={(path) => slotHint(path, Boolean(selected) && !armed, t)}
                      onSelect={setSelected}
                      onHot={setHot}
                      onPlace={(path, data) => {
                        place(path, data)
                        setDragging(false)
                        setHot(null)
                      }}
                      onDragPiece={() => setDragging(true)}
                      onDragDone={() => {
                        setDragging(false)
                        setHot(null)
                      }}
                    />
                  </div>
                </div>
              </div>
            ) : null}
            {nassi ? null : (
            <div className="composer-stage" style={{ width: scene.width * zoom, height: scene.height * zoom }}>
              <div
                className="composer-scene"
                style={{ width: scene.width, height: scene.height, transform: `scale(${zoom})` }}
                onClick={() => setSelected(null)}
              >
                <svg className="composer-wires" width={scene.width} height={scene.height} aria-hidden="true">
                  <defs>
                    <marker id="composer-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
                      <path d="M0,0 L7,3 L0,6 Z" fill="#c0392b" />
                    </marker>
                  </defs>
                  {scene.wires.map((wire, index) => {
                    if (wire.points.length < 2) return null
                    const path = wire.points.map((point, pointIndex) => `${pointIndex === 0 ? "M" : "L"}${point.x},${point.y}`).join(" ")
                    const anchor = wire.label ? labelAnchor(wire.points) : null
                    return (
                      <g key={`w${index}`}>
                        <path
                          d={path}
                          fill="none"
                          stroke="#c0392b"
                          strokeWidth={1.75}
                          markerEnd={wire.arrow ? "url(#composer-arrow)" : undefined}
                        />
                        {wire.label && anchor ? (
                          <text className="composer-flow-label" x={anchor.x} y={anchor.y}>
                            {wire.label}
                          </text>
                        ) : null}
                      </g>
                    )
                  })}
                </svg>
                {scene.nodes.map((node) => (
                  <div
                    key={node.id}
                    className={[
                      "shape",
                      `shape-${node.figure}`,
                      "composer-node",
                      selected === node.id ? "active" : "",
                      node.draggable ? "" : "is-fixed",
                    ].filter(Boolean).join(" ")}
                    style={{ left: node.x, top: node.y, width: node.width, height: node.height }}
                    draggable={!preview && node.draggable}
                    onClick={(event) => {
                      event.stopPropagation()
                      if (node.draggable || program.routines.some((item) => item.id === node.id)) setSelected(node.id)
                    }}
                    onDragStart={(event) => {
                      if (!node.draggable) {
                        event.preventDefault()
                        return
                      }
                      event.dataTransfer.setData("text/plain", `move:${node.id}`)
                      event.dataTransfer.effectAllowed = "copy"
                      setDragging(true)
                      setSelected(node.id)
                    }}
                  >
                    {node.figure === "switch" && node.cases ? (
                      <>
                        <SwitchGlyph width={node.width} height={node.height} cases={node.cases} active={selected === node.id} />
                        <span className="switch-title">{node.label}</span>
                        <div className="switch-cases">
                          {node.cases.map((item, index) => (
                            <span key={`${item.label ?? "otro"}-${index}`} style={{ width: item.width }}>
                              {spellText(locale, item.label ?? "De Otro Modo")}
                            </span>
                          ))}
                        </div>
                      </>
                    ) : (
                      <>
                        <ShapeGlyph figure={node.figure} active={selected === node.id} />
                        <span className="composer-label">
                          {node.badge ? <small>{node.badge}</small> : null}
                          {node.label}
                        </span>
                      </>
                    )}
                  </div>
                ))}
                {preview ? null : scene.slots.map((slot) => (
                  <button
                    key={slot.key}
                    type="button"
                    className={hot === slot.key ? "composer-slot hot" : "composer-slot"}
                    style={{ left: slot.x, top: slot.y, width: slot.width, height: slot.height }}
                    aria-label={slotHint(slot.path, Boolean(selected) && !armed, t)}
                    title={slotHint(slot.path, Boolean(selected) && !armed, t)}
                    onClick={(event) => {
                      event.stopPropagation()
                      if (armed) {
                        if (isRoutineKind(armed)) {
                          const created = createRoutine(armed)
                          setProgram((value) => addRoutine(value, created))
                          setSelected(created.id)
                          setArmed(null)
                          return
                        }
                        const step = createStep(armed)
                        setProgram((value) => insertStep(value, slot.path, step))
                        setSelected(step.id)
                        setArmed(null)
                        return
                      }
                      if (selected) setProgram((value) => moveStep(value, selected, slot.path))
                    }}
                    onDragOver={(event) => {
                      event.preventDefault()
                      event.dataTransfer.dropEffect = "copy"
                      setHot(slot.key)
                    }}
                    onDrop={(event) => {
                      event.preventDefault()
                      event.stopPropagation()
                      place(slot.path, event.dataTransfer.getData("text/plain"))
                      setHot(null)
                      setDragging(false)
                      setArmed(null)
                    }}
                  >
                    +
                  </button>
                ))}
              </div>
            </div>
            )}
          </div>
        </div>
        <button
          type="button"
          className={stacked ? "splitter splitter-row" : "splitter"}
          role="separator"
          aria-orientation={stacked ? "horizontal" : "vertical"}
          aria-label={t("adjustPseudocode")}
          aria-valuenow={stacked ? codeHeight : codeWidth}
          aria-valuemin={codeLimit().min}
          aria-valuemax={codeLimit().max}
          onPointerDown={(event) => {
            const narrow = window.matchMedia(NARROW).matches
            dragPane(event, narrow ? "row-resize" : "col-resize", (ev) => {
              const box = frameRef.current?.getBoundingClientRect()
              if (!box) return
              resizeCode(narrow ? box.bottom - ev.clientY : box.right - ev.clientX)
            })
          }}
          onKeyDown={(event) => {
            const step = event.shiftKey ? 48 : 16
            const current = stacked ? codeHeight : codeWidth
            if (event.key === "ArrowRight" || event.key === "ArrowUp") {
              event.preventDefault()
              resizeCode(current + step)
            }
            if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
              event.preventDefault()
              resizeCode(current - step)
            }
          }}
        />
        <aside className="composer-code">
          <div className="composer-code-head">
            <h2>{t("pseudocode")}</h2>
            <div>
              <button type="button" onClick={() => void copySource()}>
                {copied ? t("copied") : t("copy")}
              </button>
              <button type="button" onClick={downloadSource}>
                {t("download")}
              </button>
            </div>
          </div>
          {importError ? <p className="composer-banner">{t("importKept", { message: shown(importError, t) })}</p> : null}
          {importNotes.length > 0 ? (
            <ul className="composer-notes">
              {importNotes.map((note) => (
                <li key={note}>{shown(note, t)}</li>
              ))}
            </ul>
          ) : null}
          <pre className="composer-code-view" aria-live="polite">
            {colored.map((spans, index) => (
              <span key={index} className="composer-line">
                {spans.map((span, spanIndex) =>
                  span.kind && span.kind !== "variableName" ? (
                    <span key={spanIndex} className={`tok-${span.kind}`}>
                      {span.text}
                    </span>
                  ) : (
                    <span key={spanIndex}>{span.text}</span>
                  ),
                )}
                {"\n"}
              </span>
            ))}
          </pre>
          {notes.length > 0 ? (
            <ul className="composer-notes">
              {notes.map((note) => (
                <li key={note}>{shown(note, t)}</li>
              ))}
            </ul>
          ) : (
            <p className="note">{t("codeFollows")}</p>
          )}
        </aside>
      </div>
      {sendOpen ? (
        <SendDialog
          source={source}
          semicolons={semicolons}
          defaultName={passedName ?? program.name}
          onClose={() => setSendOpen(false)}
          onSent={(target) => {
            setSendOpen(false)
            onOpenInEditor(target)
          }}
        />
      ) : null}
    </div>
  )
}

function Inspector({
  step,
  routine,
  onChange,
  onChangeRoutine,
  onAddCase,
  onRemoveCase,
  onRemove,
}: {
  step: Step | null
  routine: Routine | null
  onChange: (recipe: (step: Step) => Step) => void
  onChangeRoutine: (recipe: (routine: Routine) => Routine) => void
  onAddCase: () => void
  onRemoveCase: () => void
  onRemove: () => void
}) {
  const t = useT()
  const locale = useLocale()
  return (
    <div className="composer-block inspector">
      <h2>{t("figure")}</h2>
      {!step && !routine ? <p className="note">{t("pickFigure")}</p> : null}
      {routine ? (
        <>
          <label>
            {t("nameWord")}
            <input value={routine.name} onChange={(event) => onChangeRoutine((item) => ({ ...item, name: event.target.value }))} />
          </label>
          {routine.kind === "funcion" ? (
            <label>
              {t("resultWord")}
              <input value={routine.result} onChange={(event) => onChangeRoutine((item) => ({ ...item, result: event.target.value }))} />
            </label>
          ) : null}
          <label>
            {t("parameters")}
            <input
              value={routine.params}
              placeholder={locale === "en" ? "n By Reference" : "n Por Referencia"}
              onChange={(event) => onChangeRoutine((item) => ({ ...item, params: event.target.value }))}
            />
          </label>
          <button type="button" className="inspector-remove" onClick={onRemove}>
            {routine.kind === "funcion" ? t("removeFunction") : t("removeProcedure")}
          </button>
        </>
      ) : null}
      {step?.kind === "dimension" ? (
        <>
          <label>
            {t("nameWord")}
            <input value={step.name} onChange={(event) => onChange((item) => (item.kind === "dimension" ? { ...item, name: event.target.value } : item))} />
          </label>
          <label>
            {t("sizesWord")}
            <input
              value={step.sizes}
              placeholder="5 o 2, 3"
              onChange={(event) => onChange((item) => (item.kind === "dimension" ? { ...item, sizes: event.target.value } : item))}
            />
          </label>
          <label>
            {t("typeWord")}
            <select
              value={step.typeName || "Entero"}
              onChange={(event) => onChange((item) => (item.kind === "dimension" ? { ...item, typeName: event.target.value } : item))}
            >
              {TYPE_OPTIONS.map((typeName) => (
                <option key={typeName} value={typeName}>
                  {spellText(locale, typeName)}
                </option>
              ))}
            </select>
          </label>
        </>
      ) : null}
      {step?.kind === "definir" ? (
        <>
          <label>
            {t("namesWord")}
            <input value={step.names} onChange={(event) => onChange((item) => (item.kind === "definir" ? { ...item, names: event.target.value } : item))} />
          </label>
          <label>
            {t("typeWord")}
            <select
              value={step.typeName}
              onChange={(event) => onChange((item) => (item.kind === "definir" ? { ...item, typeName: event.target.value } : item))}
            >
              {TYPE_OPTIONS.map((typeName) => (
                <option key={typeName} value={typeName}>
                  {spellText(locale, typeName)}
                </option>
              ))}
            </select>
          </label>
        </>
      ) : null}
      {step?.kind === "asignar" ? (
        <>
          <label>
            {t("destination")}
            <input
              value={step.destination}
              onChange={(event) => onChange((item) => (item.kind === "asignar" ? { ...item, destination: event.target.value } : item))}
            />
          </label>
          <label>
            {t("expression")}
            <input
              value={step.expression}
              onChange={(event) => onChange((item) => (item.kind === "asignar" ? { ...item, expression: event.target.value } : item))}
            />
          </label>
        </>
      ) : null}
      {step && (step.kind === "escribir" || step.kind === "leer" || step.kind === "esperar") ? (
        <label>
          {step.kind === "escribir" ? t("valuesWord") : step.kind === "leer" ? t("destinations") : t("seconds")}
          <textarea
            rows={3}
            value={step.text}
            onChange={(event) => {
              const text = event.target.value
              onChange((item) =>
                item.kind === "escribir" || item.kind === "leer" || item.kind === "esperar" ? { ...item, text } : item,
              )
            }}
          />
        </label>
      ) : null}
      {step && (step.kind === "si" || step.kind === "mientras" || step.kind === "repetir") ? (
        <label>
          {t("conditionWord")}
          <textarea
            rows={3}
            value={step.condition}
            onChange={(event) => {
              const condition = event.target.value
              onChange((item) =>
                item.kind === "si" || item.kind === "mientras" || item.kind === "repetir" ? { ...item, condition } : item,
              )
            }}
          />
        </label>
      ) : null}
      {step?.kind === "para" ? (
        <>
          <label>
            {t("figVariable")}
            <input value={step.variable} onChange={(event) => onChange((item) => (item.kind === "para" ? { ...item, variable: event.target.value } : item))} />
          </label>
          <label>
            {t("fromWord")}
            <input value={step.from} onChange={(event) => onChange((item) => (item.kind === "para" ? { ...item, from: event.target.value } : item))} />
          </label>
          <label>
            {t("untilWord")}
            <input value={step.to} onChange={(event) => onChange((item) => (item.kind === "para" ? { ...item, to: event.target.value } : item))} />
          </label>
          <label>
            {t("stepSize")}
            <input value={step.step} onChange={(event) => onChange((item) => (item.kind === "para" ? { ...item, step: event.target.value } : item))} />
          </label>
        </>
      ) : null}
      {step?.kind === "segun" ? (
        <>
          <label>
            {t("expression")}
            <input
              value={step.expression}
              onChange={(event) => onChange((item) => (item.kind === "segun" ? { ...item, expression: event.target.value } : item))}
            />
          </label>
          {step.cases.map((item, index) => (
            <label key={item.id}>
              {t("caseN", { number: index + 1 })}
              <input
                value={item.label}
                onChange={(event) => {
                  const label = event.target.value
                  onChange((current) =>
                    current.kind === "segun"
                      ? { ...current, cases: current.cases.map((branch) => (branch.id === item.id ? { ...branch, label } : branch)) }
                      : current,
                  )
                }}
              />
            </label>
          ))}
          <div className="inspector-actions">
            <button type="button" onClick={onAddCase} disabled={step.cases.length >= 6}>
              {t("addCase")}
            </button>
            <button type="button" onClick={onRemoveCase} disabled={step.cases.length <= 1}>
              {t("removeCase")}
            </button>
          </div>
        </>
      ) : null}
      {step?.kind === "borrar" ? <p className="note">{t("clearsConsole")}</p> : null}
      {step?.kind === "comentario" ? (
        <label>
          {t("commentWord")}
          <textarea
            rows={3}
            value={step.text}
            onChange={(event) => {
              const text = event.target.value
              onChange((item) => (item.kind === "comentario" ? { ...item, text } : item))
            }}
          />
        </label>
      ) : null}
      {step?.kind === "libre" ? (
        <label>
          {t("instruction")}
          <textarea
            rows={3}
            value={step.text}
            onChange={(event) => {
              const text = event.target.value
              onChange((item) => (item.kind === "libre" ? { ...item, text } : item))
            }}
          />
        </label>
      ) : null}
      {step ? (
        <button type="button" className="inspector-remove" onClick={onRemove}>
          {t("removeFigure")}
        </button>
      ) : null}
    </div>
  )
}

function SendDialog({
  source,
  semicolons,
  defaultName,
  onClose,
  onSent,
}: {
  source: string
  semicolons: boolean
  defaultName: string
  onClose: () => void
  onSent: (target: { projectId: string; algorithmId: string }) => void
}) {
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [projectId, setProjectId] = useState("")
  const [newProject, setNewProject] = useState(false)
  const [projectName, setProjectName] = useState("")
  const [name, setName] = useState(defaultName)
  const [listed, setListed] = useState<Algorithm[] | null>(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const t = useT()
  const algorithmName = name.trim()
  const existing =
    !newProject && listed ? (listed.find((item) => item.folder_id == null && item.name === algorithmName) ?? null) : null

  useEffect(() => {
    let current = true
    void api
      .projects()
      .then((page) => {
        if (!current) return
        setProjects(page.results)
        if (page.results.length === 0) setNewProject(true)
        else setProjectId(page.results[0].id)
      })
      .catch((caught: unknown) => {
        if (!current) return
        setProjects([])
        setNewProject(true)
        setError(caught instanceof Error ? caught.message : "No se pudieron cargar los proyectos.")
      })
    return () => {
      current = false
    }
  }, [])

  useEffect(() => {
    if (!projectId || newProject) {
      setListed(newProject ? [] : null)
      return
    }
    let current = true
    setListed(null)
    void projectAlgorithms(projectId)
      .then((items) => {
        if (current) setListed(items)
      })
      .catch((caught: unknown) => {
        if (!current) return
        setListed([])
        setError(caught instanceof Error ? caught.message : "No se pudieron cargar los algoritmos.")
      })
    return () => {
      current = false
    }
  }, [projectId, newProject])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [busy, onClose])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!algorithmName) {
      setError(t("writeAlgorithmName"))
      return
    }
    setBusy(true)
    setError("")
    let destination = projectId
    try {
      if (newProject) {
        const title = projectName.trim()
        if (!title) {
          setError(t("writeProjectName"))
          setBusy(false)
          return
        }
        const project = await api.createProject(title)
        destination = project.id
      }
      if (!destination) {
        setError(t("pickProject"))
        setBusy(false)
        return
      }
      const known = newProject ? [] : (listed ?? (await projectAlgorithms(destination)))
      const match = known.find((item) => item.folder_id == null && item.name === algorithmName) ?? null
      if (match) {
        await api.saveSource(match.id, source)
        await api.saveLanguageOptions(match.id, { require_semicolons: semicolons })
        onSent({ projectId: destination, algorithmId: match.id })
        return
      }
      const algorithm = await api.createAlgorithm(destination, algorithmName, source)
      await api.saveLanguageOptions(algorithm.id, { require_semicolons: semicolons })
      onSent({ projectId: destination, algorithmId: algorithm.id })
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "No se pudo guardar el algoritmo."
      if (destination && message.includes("Ya existe")) {
        try {
          const fresh = await projectAlgorithms(destination)
          setListed(fresh)
          if (fresh.some((item) => item.folder_id == null && item.name === algorithmName)) {
            setError(`Ya existe «${algorithmName}». Confirma si quieres reemplazar su código.`)
            setBusy(false)
            return
          }
        } catch {
          // The message below still explains the collision.
        }
      }
      setError(message)
      setBusy(false)
    }
  }

  return (
    <div
      className="composer-modal"
      role="presentation"
      onClick={() => {
        if (!busy) onClose()
      }}
    >
      <form
        className="composer-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="send-diagram-title"
        onClick={(event) => event.stopPropagation()}
        onSubmit={(event) => void submit(event)}
      >
        <h2 id="send-diagram-title">{t("sendToEditor")}</h2>
        <p className="note">{t("sendNote")}</p>
        {projects === null ? <p className="note">{t("loadingProjects")}</p> : null}
        {projects && projects.length > 0 ? (
          <label>
            {t("project")}
            <select
              autoFocus
              value={projectId}
              disabled={newProject}
              onChange={(event) => setProjectId(event.target.value)}
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="composer-check">
          <input type="checkbox" checked={newProject} onChange={(event) => setNewProject(event.target.checked)} />
          {t("newProjectCheck")}
        </label>
        {newProject ? (
          <label>
            {t("projectName")}
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} autoFocus />
          </label>
        ) : null}
        <label>
          {t("algorithmName")}
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        {existing ? <p className="composer-banner">{t("replaceBanner", { name: existing.name })}</p> : null}
        {error ? <p className="composer-banner">{shown(error, t)}</p> : null}
        <div className="composer-dialog-actions">
          <button type="button" onClick={onClose} disabled={busy}>
            {t("cancel")}
          </button>
          <button type="submit" className="primary" disabled={busy || projects === null || (!newProject && listed === null)}>
            {busy ? t("saving") : existing ? t("replaceOpen") : t("createOpen")}
          </button>
        </div>
      </form>
    </div>
  )
}

async function projectAlgorithms(projectId: string): Promise<Algorithm[]> {
  const first = await api.algorithms(projectId)
  if (first.results.length >= first.count) return first.results
  const second = await api.algorithms(projectId, 2)
  return [...first.results, ...second.results]
}
