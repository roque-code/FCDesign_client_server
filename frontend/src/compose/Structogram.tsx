import { createContext, Fragment, useContext, type DragEvent, type MouseEvent, type ReactNode } from "react"

import type { Dialect } from "../dialect"
import { translate } from "../i18n"
import { caption, routineTitle, slotKey, type Program, type Routine, type SlotPath, type Step } from "./model"

type PaletteKind = Step["kind"] | Routine["kind"]

type NsApi = {
  locale: Dialect
  selected: string | null
  armed: string | null
  preview: boolean
  dragging: boolean
  hot: string | null
  hint: (path: SlotPath) => string
  onSelect: (id: string) => void
  onHot: (key: string | null) => void
  onPlace: (path: SlotPath, data: string) => void
  onDragPiece: () => void
  onDragDone: () => void
}

const NsContext = createContext<NsApi | null>(null)

function useNs(): NsApi {
  const api = useContext(NsContext)
  if (!api) throw new Error("Structogram sin contexto.")
  return api
}

function word(locale: Dialect, es: string, en: string): string {
  return locale === "en" ? en : es
}

function shown(step: Step, locale: Dialect): string {
  return caption(step, locale).replaceAll(" <- ", " ← ")
}

const SAMPLES: Record<string, [string, string]> = {
  comentario: ["// …", "// …"],
  asignar: ["A ← B+i", "A ← B+i"],
  escribir: ["Escribir …", "Write …"],
  leer: ["Leer …", "Read …"],
  mientras: ["Mientras …", "While …"],
  repetir: ["Hasta que…", "Until…"],
  para: ["Para …", "For …"],
  definir: ["Definir", "Declare"],
  borrar: ["Borrar", "Clear"],
  esperar: ["Esperar", "Wait"],
  funcion: ["Función", "Function"],
  procedimiento: ["Subproceso", "Subroutine"],
}

export function NsIcon({ kind, locale }: { kind: PaletteKind; locale: Dialect }) {
  if (kind === "si") {
    return (
      <span className="ns-icon ns-icon-si">
        <svg viewBox="0 0 86 40" aria-hidden="true">
          <rect x="0.5" y="0.5" width="85" height="39" fill="#fffdf8" stroke="#3f382f" />
          <polyline points="8,7 43,33 78,7" fill="none" stroke="#3f382f" strokeWidth="1.3" />
        </svg>
        <span className="ns-mini-yes">{word(locale, "Si", "If")}</span>
        <span className="ns-mini-no">No</span>
        <span className="ns-mini-x">X</span>
      </span>
    )
  }
  if (kind === "segun") {
    return (
      <span className="ns-icon ns-icon-segun">
        <svg viewBox="0 0 86 40" aria-hidden="true">
          <rect x="0.5" y="0.5" width="85" height="39" fill="#fffdf8" stroke="#3f382f" />
          <line x1="30" y1="1" x2="22" y2="39" stroke="#3f382f" />
          <line x1="58" y1="1" x2="50" y2="39" stroke="#3f382f" />
        </svg>
        <span className="ns-mini-c1">1</span>
        <span className="ns-mini-c2">2</span>
        <span className="ns-mini-c3">X</span>
      </span>
    )
  }
  const pair = SAMPLES[kind] ?? ["…", "…"]
  return (
    <span className={`ns-icon ns-icon-${kind}`}>
      <span className="ns-icon-text">{pair[locale === "en" ? 1 : 0]}</span>
    </span>
  )
}

export function Structogram({
  program,
  locale,
  selected,
  armed,
  preview,
  dragging,
  hot,
  hint,
  onSelect,
  onHot,
  onPlace,
  onDragPiece,
  onDragDone,
}: NsApi & { program: Program }) {
  return (
    <NsContext.Provider
      value={{ locale, selected, armed, preview, dragging, hot, hint, onSelect, onHot, onPlace, onDragPiece, onDragDone }}
    >
      <div className="ns-stack" role="group" aria-label={translate(locale, "diagramNs")}>
        <div className="ns-frame">
          <NsList steps={program.body} pathAt={(index) => ({ scope: "root", index })} />
        </div>
        {program.routines.map((routine) => (
          <RoutineFrame key={routine.id} routine={routine} />
        ))}
      </div>
    </NsContext.Provider>
  )
}

function RoutineFrame({ routine }: { routine: Routine }) {
  const api = useNs()
  return (
    <div className="ns-frame">
      <div
        className={`ns-step ns-kind-routine${api.selected === routine.id ? " is-selected" : ""}`}
        onClick={(event) => {
          event.stopPropagation()
          api.onSelect(routine.id)
        }}
        aria-selected={api.selected === routine.id}
      >
        <div className="ns-cell ns-routine-title">{routineTitle(routine, api.locale).replaceAll(" <- ", " ← ")}</div>
      </div>
      <NsList steps={routine.body} pathAt={(index) => ({ scope: "routine", ownerId: routine.id, index })} />
    </div>
  )
}

function NsList({ steps, pathAt }: { steps: Step[]; pathAt: (index: number) => SlotPath }) {
  const api = useNs()
  return (
    <div className={steps.length === 0 ? "ns-list is-empty" : "ns-list"}>
      {steps.length === 0 ? (
        api.preview ? (
          <div className="ns-step">
            <div className="ns-cell">
              <div className="ns-blank" />
            </div>
          </div>
        ) : (
          <NsSlot path={pathAt(0)} empty />
        )
      ) : (
        <>
          {api.preview ? null : <NsSlot path={pathAt(0)} />}
          {steps.map((step, index) => (
            <Fragment key={step.id}>
              <NsStep step={step} />
              {api.preview ? null : <NsSlot path={pathAt(index + 1)} />}
            </Fragment>
          ))}
        </>
      )}
    </div>
  )
}

function NsSlot({ path, empty = false }: { path: SlotPath; empty?: boolean }) {
  const api = useNs()
  const key = slotKey(path)
  return (
    <div className="ns-slot-row">
      <div className="ns-cell">
        <button
          type="button"
          className={api.hot === key ? "ns-slot hot" : "ns-slot"}
          aria-label={api.hint(path)}
          title={api.hint(path)}
          onClick={(event) => {
            event.stopPropagation()
            if (api.armed) api.onPlace(path, `piece:${api.armed}`)
            else if (api.selected) api.onPlace(path, `move:${api.selected}`)
          }}
          onDragStart={(event) => {
            event.preventDefault()
            event.stopPropagation()
          }}
          onDragOver={(event) => {
            event.preventDefault()
            event.stopPropagation()
            event.dataTransfer.dropEffect = "copy"
            api.onHot(key)
          }}
          onDrop={(event) => {
            event.preventDefault()
            event.stopPropagation()
            api.onPlace(path, event.dataTransfer.getData("text/plain"))
            api.onDragDone()
          }}
        >
          {empty && !api.dragging ? translate(api.locale, "nsDrop") : "+"}
        </button>
      </div>
    </div>
  )
}

function LoopBody({ step, label, footer = false }: { step: Extract<Step, { kind: "mientras" | "para" | "repetir" }>; label: string; footer?: boolean }) {
  const bar = <div className={footer ? "ns-loop-bar ns-loop-bar-end" : "ns-loop-bar"}>{label}</div>
  const body = (
    <div className="ns-loop-split">
      <div className="ns-rail" />
      <div className="ns-loop-inner">
        <div className="ns-nest">
          <NsList steps={step.body} pathAt={(index) => ({ scope: "body", ownerId: step.id, index })} />
        </div>
      </div>
    </div>
  )
  return (
    <div className="ns-cell">
      {footer ? null : bar}
      {body}
      {footer ? bar : null}
    </div>
  )
}

function NsStep({ step }: { step: Step }) {
  const api = useNs()
  const selected = api.selected === step.id
  const onClick = (event: MouseEvent) => {
    event.stopPropagation()
    api.onSelect(step.id)
  }
  const onDragStart = (event: DragEvent) => {
    if (api.preview) {
      event.preventDefault()
      return
    }
    event.stopPropagation()
    event.dataTransfer.setData("text/plain", `move:${step.id}`)
    event.dataTransfer.effectAllowed = "copy"
    api.onDragPiece()
    api.onSelect(step.id)
  }
  const shell = (body: ReactNode, block = false) => (
    <div
      className={["ns-step", `ns-kind-${step.kind}`, block ? "ns-block" : "ns-row", selected ? "is-selected" : ""].filter(Boolean).join(" ")}
      draggable={!api.preview}
      onClick={onClick}
      onDragStart={onDragStart}
      aria-selected={selected}
    >
      {body}
    </div>
  )

  if (step.kind === "si") {
    return shell(
      <div className="ns-cell">
        <div className="ns-if-head">
          <svg viewBox="0 0 200 52" preserveAspectRatio="none" aria-hidden="true">
            <polygon points="0,0 200,0 100,52" fill="rgba(255,255,255,0.28)" stroke="#3f382f" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          </svg>
          <span className="ns-if-cond">{shown(step, api.locale)}</span>
          <span className="ns-if-yes">{word(api.locale, "Si", "If")}</span>
          <span className="ns-if-no">No</span>
        </div>
        <div className="ns-split">
          <div className="ns-col">
            <div className="ns-nest">
              <NsList steps={step.then} pathAt={(index) => ({ scope: "then", ownerId: step.id, index })} />
            </div>
          </div>
          <div className="ns-col">
            <div className="ns-nest">
              <NsList steps={step.else} pathAt={(index) => ({ scope: "else", ownerId: step.id, index })} />
            </div>
          </div>
        </div>
      </div>,
      true,
    )
  }

  if (step.kind === "mientras" || step.kind === "para") {
    const label =
      step.kind === "mientras"
        ? `${word(api.locale, "Mientras", "While")} ${shown(step, api.locale)}`
        : `${word(api.locale, "Para", "For")} ${shown(step, api.locale)}`
    return shell(<LoopBody step={step} label={label} />, true)
  }

  if (step.kind === "repetir") {
    return shell(
      <LoopBody step={step} label={`${word(api.locale, "Hasta que", "Until")} ${shown(step, api.locale)}`} footer />,
      true,
    )
  }

  if (step.kind === "segun") {
    const columns = [
      ...step.cases.map((item) => ({ key: item.id, label: item.label || "…", steps: item.body, pathAt: (index: number) => ({ scope: "case" as const, ownerId: step.id, caseId: item.id, index }) })),
      {
        key: "other",
        label: word(api.locale, "Otro", "Other"),
        steps: step.other,
        pathAt: (index: number) => ({ scope: "other" as const, ownerId: step.id, index }),
      },
    ]
    return shell(
      <div className="ns-cell">
        <div className="ns-switch-expr">
          {word(api.locale, "Según", "Switch")} {shown(step, api.locale)}
        </div>
        <div className="ns-split">
          {columns.map((column, index) => (
            <div key={column.key} className="ns-col">
              <div className="ns-case-label">
                {index > 0 ? (
                  <svg className="ns-case-slash" viewBox="0 0 16 28" preserveAspectRatio="none" aria-hidden="true">
                    <line x1="16" y1="0" x2="0" y2="28" stroke="#3f382f" strokeWidth="1" vectorEffect="non-scaling-stroke" />
                  </svg>
                ) : null}
                <span>{column.label}</span>
              </div>
              <div className="ns-nest">
                <NsList steps={column.steps} pathAt={column.pathAt} />
              </div>
            </div>
          ))}
        </div>
      </div>,
      true,
    )
  }

  return shell(
    <div className="ns-cell">
      <span className="ns-label">{shown(step, api.locale)}</span>
    </div>,
  )
}
