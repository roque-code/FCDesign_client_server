import type { Dialect } from "../dialect"
import type { GlyphCase } from "../diagram/glyphs"
import {
  badgeFor,
  caption,
  figureForKind,
  routineTitle,
  slotKey,
  type Program,
  type Routine,
  type SlotPath,
  type Step,
} from "./model"

let spoken: Dialect = "es"

function yes(): string {
  return spoken === "en" ? "T" : "V"
}

function no(): string {
  return "F"
}

export type Point = { x: number; y: number }

export type PlacedNode = {
  id: string
  figure: string
  label: string
  badge: string | null
  x: number
  y: number
  width: number
  height: number
  cases: GlyphCase[] | null
  draggable: boolean
}

export type DropSlot = {
  key: string
  path: SlotPath
  x: number
  y: number
  width: number
  height: number
}

export type Wire = {
  points: Point[]
  label: string | null
  arrow: boolean
}

export type Scene = {
  width: number
  height: number
  nodes: PlacedNode[]
  wires: Wire[]
  slots: DropSlot[]
}

type Rect = { x: number; y: number; width: number; height: number }

type Fragment = {
  placed: PlacedNode[]
  wires: Wire[]
  slots: DropSlot[]
  entry: Point
  aim: Point
  exit: Point
  bounds: Rect
}

const OPEN_GAP = 56
const CLOSED_GAP = 22
let listGap = CLOSED_GAP
const SLOT_W = 120
const SLOT_H = 28
const SIDE = 32
const PAD = 40

function boxSize(label: string, figure: string): { width: number; height: number } {
  const longest = Math.max(...label.split("\n").map((line) => [...line].length), 8)
  const char = 6.5
  if (figure === "decision") {
    const width = Math.min(340, Math.max(210, Math.round(longest * 4.8 + 72)))
    const lines = Math.max(1, Math.ceil((longest * char) / (width * 0.56)))
    return { width, height: Math.max(128, 64 + lines * 15) }
  }
  if (figure === "loop") {
    const width = Math.min(360, Math.max(230, Math.round(longest * 5 + 84)))
    const lines = Math.max(1, Math.ceil((longest * char) / (width * 0.58)))
    return { width, height: Math.max(112, 58 + lines * 15) }
  }
  if (figure === "terminal") {
    return { width: Math.min(220, Math.max(168, longest * 10 + 36)), height: 56 }
  }
  const width = Math.min(300, Math.max(210, Math.round(longest * 4.6 + 56)))
  const lines = Math.max(1, Math.ceil((longest * char) / (width * 0.82)))
  return { width, height: Math.max(58, 28 + lines * 17) }
}

function slotAt(axis: number, gapTop: number, path: SlotPath, index: number): DropSlot {
  const here = { ...path, index }
  const height = Math.min(SLOT_H, Math.max(8, listGap - 6))
  return {
    key: slotKey(here),
    path: here,
    x: axis - SLOT_W / 2,
    y: gapTop + (listGap - height) / 2,
    width: SLOT_W,
    height,
  }
}

function enclose(parts: { placed: PlacedNode[]; slots: DropSlot[]; wires: Wire[]; extra?: Point[] }): Rect {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  const add = (x: number, y: number, width = 0, height = 0) => {
    minX = Math.min(minX, x)
    minY = Math.min(minY, y)
    maxX = Math.max(maxX, x + width)
    maxY = Math.max(maxY, y + height)
  }
  for (const node of parts.placed) add(node.x, node.y, node.width, node.height)
  for (const slot of parts.slots) add(slot.x, slot.y, slot.width, slot.height)
  for (const wire of parts.wires) {
    for (const point of wire.points) add(point.x, point.y)
  }
  for (const point of parts.extra ?? []) add(point.x, point.y)
  if (!Number.isFinite(minX)) return { x: 0, y: 0, width: 0, height: 0 }
  return { x: minX, y: minY, width: Math.max(1, maxX - minX), height: Math.max(1, maxY - minY) }
}

function translate(fragment: Fragment, dx: number, dy: number): Fragment {
  const shift = (point: Point): Point => ({ x: point.x + dx, y: point.y + dy })
  return {
    placed: fragment.placed.map((node) => ({ ...node, x: node.x + dx, y: node.y + dy })),
    wires: fragment.wires.map((wire) => ({ ...wire, points: wire.points.map(shift) })),
    slots: fragment.slots.map((slot) => ({ ...slot, x: slot.x + dx, y: slot.y + dy })),
    entry: shift(fragment.entry),
    aim: shift(fragment.aim),
    exit: shift(fragment.exit),
    bounds: { ...fragment.bounds, x: fragment.bounds.x + dx, y: fragment.bounds.y + dy },
  }
}

function line(points: Point[], label: string | null, arrow: boolean): Wire {
  const compact: Point[] = []
  for (const point of points) {
    const previous = compact[compact.length - 1]
    if (previous && Math.abs(previous.x - point.x) < 0.5 && Math.abs(previous.y - point.y) < 0.5) continue
    compact.push(point)
  }
  return { points: compact, label, arrow }
}

function leaf(
  id: string,
  figure: string,
  label: string,
  badge: string | null,
  axis: number,
  top: number,
  cases: GlyphCase[] | null = null,
): Fragment {
  const size = cases ? { width: cases.reduce((sum, item) => sum + item.width, 0), height: 108 } : boxSize(label, figure)
  const x = axis - size.width / 2
  const placed: PlacedNode[] = [
    {
      id,
      figure,
      label,
      badge,
      x,
      y: top,
      width: size.width,
      height: size.height,
      cases,
      draggable: id !== "start" && id !== "end",
    },
  ]
  return {
    placed,
    wires: [],
    slots: [],
    entry: { x: axis, y: top },
    aim: { x: axis, y: top },
    exit: { x: axis, y: top + size.height },
    bounds: { x, y: top, width: size.width, height: size.height },
  }
}

function layoutList(steps: Step[], axis: number, top: number, path: SlotPath, closeArrow: boolean): Fragment {
  const slots: DropSlot[] = [slotAt(axis, top, path, 0)]
  const wires: Wire[] = []
  const placed: PlacedNode[] = []
  if (steps.length === 0) {
    const entry = { x: axis, y: top }
    const exit = { x: axis, y: top + listGap }
    const fragment = {
      placed,
      wires: [line([entry, exit], null, closeArrow)],
      slots,
      entry,
      aim: { x: axis, y: top + listGap / 2 },
      exit,
      bounds: enclose({ placed, slots, wires: [line([entry, exit], null, closeArrow)], extra: [entry, exit] }),
    }
    return fragment
  }
  let cursor = top + listGap
  let previous: Point | null = null
  const children: Fragment[] = []
  for (let index = 0; index < steps.length; index += 1) {
    const child = layoutStep(steps[index], axis, cursor)
    children.push(child)
    placed.push(...child.placed)
    wires.push(...child.wires)
    slots.push(...child.slots)
    const from = previous ?? { x: axis, y: top }
    wires.push(line([from, child.aim], null, true))
    previous = child.exit
    slots.push(slotAt(axis, child.exit.y, path, index + 1))
    cursor = child.exit.y + listGap
  }
  const exit = { x: axis, y: previous ? previous.y + listGap : top + listGap }
  if (previous) wires.push(line([previous, exit], null, closeArrow))
  const entry = { x: axis, y: top }
  return {
    placed,
    wires,
    slots,
    entry,
    aim: children[0].aim,
    exit,
    bounds: enclose({ placed, slots, wires, extra: [entry, exit] }),
  }
}

function elbow(from: Point, to: Point, label: string): Wire {
  return line([from, { x: to.x, y: from.y }, to], label, false)
}

function joinWire(from: Point, center: number, joinY: number): Wire {
  return line([from, { x: from.x, y: joinY }, { x: center, y: joinY }], null, false)
}

function layoutSi(step: Extract<Step, { kind: "si" }>, axis: number, top: number): Fragment {
  const head = leaf(step.id, "decision", caption(step, spoken), badgeFor(step.kind, spoken), axis, top)
  const else0 = layoutList(step.else, 0, 0, { scope: "else", ownerId: step.id, index: 0 }, false)
  const then0 = layoutList(step.then, 0, 0, { scope: "then", ownerId: step.id, index: 0 }, false)
  const diamondLeft = axis - head.bounds.width / 2
  const diamondRight = axis + head.bounds.width / 2
  const branchTop = top + head.bounds.height + 10
  const elseFrag = translate(
    else0,
    diamondLeft - SIDE - (else0.bounds.x + else0.bounds.width),
    branchTop - else0.bounds.y,
  )
  const thenFrag = translate(then0, diamondRight + SIDE - then0.bounds.x, branchTop - then0.bounds.y)
  const sideY = top + head.bounds.height / 2
  const wires = [
    elbow({ x: diamondLeft, y: sideY }, elseFrag.entry, no()),
    elbow({ x: diamondRight, y: sideY }, thenFrag.entry, yes()),
    ...elseFrag.wires,
    ...thenFrag.wires,
  ]
  const joinY = Math.max(elseFrag.exit.y, thenFrag.exit.y) + 18
  wires.push(joinWire(elseFrag.exit, axis, joinY))
  wires.push(joinWire(thenFrag.exit, axis, joinY))
  const placed = [...head.placed, ...elseFrag.placed, ...thenFrag.placed]
  const slots = [...elseFrag.slots, ...thenFrag.slots]
  const exit = { x: axis, y: joinY }
  return {
    placed,
    wires,
    slots,
    entry: head.entry,
    aim: head.aim,
    exit,
    bounds: enclose({ placed, slots, wires, extra: [head.entry, exit] }),
  }
}

function layoutLoop(step: Extract<Step, { kind: "mientras" | "para" }>, axis: number, top: number): Fragment {
  const head = leaf(step.id, "loop", caption(step, spoken), badgeFor(step.kind, spoken), axis, top)
  const body0 = layoutList(step.body, 0, 0, { scope: "body", ownerId: step.id, index: 0 }, false)
  const bodyTop = top + head.bounds.height / 2
  const body = translate(body0, axis + head.bounds.width / 2 + SIDE - body0.bounds.x, bodyTop - body0.bounds.y)
  const leftX = Math.min(axis - head.bounds.width / 2, body.bounds.x) - 36
  const rightX = Math.max(axis + head.bounds.width / 2, body.bounds.x + body.bounds.width) + 28
  const joinY = Math.max(top + head.bounds.height, body.exit.y) + 20
  const sideY = top + head.bounds.height / 2
  const wires = [
    elbow({ x: axis + head.bounds.width / 2, y: sideY }, body.entry, yes()),
    line(
      [
        { x: axis - head.bounds.width / 2, y: sideY },
        { x: leftX, y: sideY },
        { x: leftX, y: joinY },
        { x: axis, y: joinY },
      ],
      no(),
      false,
    ),
    line(
      [
        body.exit,
        { x: rightX, y: body.exit.y },
        { x: rightX, y: top - 12 },
        { x: axis + head.bounds.width * 0.3, y: top - 12 },
        { x: axis + head.bounds.width * 0.3, y: top + 1 },
      ],
      null,
      true,
    ),
    ...body.wires,
  ]
  const placed = [...head.placed, ...body.placed]
  const exit = { x: axis, y: joinY }
  return {
    placed,
    wires,
    slots: body.slots,
    entry: head.entry,
    aim: head.aim,
    exit,
    bounds: enclose({ placed, slots: body.slots, wires, extra: [head.entry, exit] }),
  }
}

function layoutRepeat(step: Extract<Step, { kind: "repetir" }>, axis: number, top: number): Fragment {
  const body = layoutList(step.body, axis, top, { scope: "body", ownerId: step.id, index: 0 }, false)
  const head = leaf(step.id, "loop", caption(step, spoken), badgeFor(step.kind, spoken), axis, body.exit.y + 12)
  const leftX = Math.min(axis - head.bounds.width / 2, body.bounds.x) - 36
  const rightX = axis + head.bounds.width / 2 + 32
  const sideY = head.aim.y + head.bounds.height / 2
  const exitY = head.exit.y + 26
  const wires = [
    ...body.wires,
    line([body.exit, head.aim], null, true),
    line(
      [
        { x: axis - head.bounds.width / 2, y: sideY },
        { x: leftX, y: sideY },
        { x: leftX, y: body.aim.y },
        body.aim,
      ],
      no(),
      true,
    ),
    line(
      [
        { x: axis + head.bounds.width / 2, y: sideY },
        { x: rightX, y: sideY },
        { x: rightX, y: exitY },
        { x: axis, y: exitY },
      ],
      yes(),
      false,
    ),
  ]
  const placed = [...body.placed, ...head.placed]
  const exit = { x: axis, y: exitY }
  return {
    placed,
    wires,
    slots: body.slots,
    entry: body.entry,
    aim: body.aim,
    exit,
    bounds: enclose({ placed, slots: body.slots, wires, extra: [body.entry, exit] }),
  }
}

function layoutSwitch(step: Extract<Step, { kind: "segun" }>, axis: number, top: number): Fragment {
  const columns = [
    ...step.cases.map((item) => ({
      label: item.label.trim() || "caso",
      steps: item.body,
      path: { scope: "case" as const, ownerId: step.id, caseId: item.id, index: 0 },
    })),
    { label: null as string | null, steps: step.other, path: { scope: "other" as const, ownerId: step.id, index: 0 } },
  ]
  const drafted = columns.map((column) => layoutList(column.steps, 0, 0, column.path, false))
  const widths = drafted.map((fragment) => Math.max(132, fragment.bounds.width))
  const total = widths.reduce((sum, width) => sum + width, 0)
  const cases: GlyphCase[] = columns.map((column, index) => ({ label: column.label, width: widths[index] }))
  const head = leaf(step.id, "switch", caption(step, spoken), badgeFor(step.kind, spoken), axis, top, cases)
  const headerBottom = top + head.bounds.height
  let cursor = axis - total / 2
  const placed = [...head.placed]
  const slots: DropSlot[] = []
  const wires: Wire[] = []
  const exits: Point[] = []
  drafted.forEach((fragment, index) => {
    const center = cursor + widths[index] / 2
    const moved = translate(fragment, center - (fragment.bounds.x + fragment.bounds.width / 2), headerBottom + 8 - fragment.bounds.y)
    placed.push(...moved.placed)
    slots.push(...moved.slots)
    wires.push(...moved.wires)
    wires.push(line([{ x: cursor + widths[index] / 2, y: headerBottom }, moved.entry], null, false))
    exits.push(moved.exit)
    cursor += widths[index]
  })
  const joinY = Math.max(...exits.map((point) => point.y)) + 18
  for (const point of exits) wires.push(joinWire(point, axis, joinY))
  const exit = { x: axis, y: joinY }
  return {
    placed,
    wires,
    slots,
    entry: head.entry,
    aim: head.aim,
    exit,
    bounds: enclose({ placed, slots, wires, extra: [head.entry, exit] }),
  }
}

function layoutStep(step: Step, axis: number, top: number): Fragment {
  switch (step.kind) {
    case "si":
      return layoutSi(step, axis, top)
    case "mientras":
    case "para":
      return layoutLoop(step, axis, top)
    case "repetir":
      return layoutRepeat(step, axis, top)
    case "segun":
      return layoutSwitch(step, axis, top)
    default: {
      const figure = step.kind === "libre" && step.call ? "subprocess" : figureForKind(step.kind)
      return leaf(step.id, figure, caption(step, spoken), null, axis, top)
    }
  }
}

export function layoutProgram(program: Program, locale: Dialect = "es", spread = false): Scene {
  spoken = locale
  listGap = spread ? OPEN_GAP : CLOSED_GAP
  const main = layoutMain(program)
  const routines = program.routines.map(layoutRoutine)
  if (routines.length === 0) return main
  const gap = 36
  let top = main.height + 8
  const nodes = [...main.nodes]
  const wires = [...main.wires]
  const slots = [...main.slots]
  let width = main.width
  let height = main.height
  for (const fragment of routines) {
    let dx = (main.width - fragment.bounds.width) / 2 - fragment.bounds.x
    if (fragment.bounds.x + dx < PAD) dx = PAD - fragment.bounds.x
    const moved = translate(fragment, dx, top - fragment.bounds.y)
    nodes.push(...moved.placed)
    wires.push(...moved.wires)
    slots.push(...moved.slots)
    top = moved.bounds.y + moved.bounds.height + gap
    width = Math.max(width, moved.bounds.x + moved.bounds.width + PAD)
    height = Math.max(height, top + PAD)
  }
  return { width: Math.ceil(width), height: Math.ceil(height), nodes, wires, slots }
}

function layoutMain(program: Program): Scene {
  const start = leaf("start", "terminal", spoken === "en" ? "Start" : "Inicio", null, 0, PAD)
  const flow = layoutList(program.body, 0, start.exit.y, { scope: "root", index: 0 }, true)
  const end = leaf("end", "terminal", spoken === "en" ? "End" : "Fin", null, 0, flow.exit.y)
  const placed = [...start.placed, ...flow.placed, ...end.placed]
  const wires = flow.wires
  const slots = flow.slots
  const bounds = enclose({ placed, slots, wires, extra: [start.entry, end.exit] })
  const dx = PAD - bounds.x
  const dy = PAD - bounds.y
  const shift = (point: Point): Point => ({ x: point.x + dx, y: point.y + dy })
  const nodes = placed.map((node) => ({ ...node, x: node.x + dx, y: node.y + dy }))
  return {
    width: Math.ceil(bounds.width + PAD * 2),
    height: Math.ceil(bounds.height + PAD * 2),
    nodes,
    wires: wires.map((wire) => ({ ...wire, points: wire.points.map(shift) })),
    slots: slots.map((slot) => ({ ...slot, x: slot.x + dx, y: slot.y + dy })),
  }
}

function layoutRoutine(routine: Routine): Fragment {
  const start = leaf(
    routine.id,
    "subprocess",
    routineTitle(routine, spoken),
    routine.kind === "funcion" ? (spoken === "en" ? "Function" : "Función") : spoken === "en" ? "SubProcedure" : "Procedimiento",
    0,
    0,
  )
  start.placed[0].draggable = false
  const flow = layoutList(routine.body, 0, start.exit.y, { scope: "routine", ownerId: routine.id, index: 0 }, true)
  const end = leaf(
    `${routine.id}:fin`,
    "terminal",
    routine.kind === "funcion" ? (spoken === "en" ? "EndFunction" : "FinFuncion") : spoken === "en" ? "EndSubProcedure" : "FinSubProceso",
    null,
    0,
    flow.exit.y,
  )
  end.placed[0].draggable = false
  const placed = [...start.placed, ...flow.placed, ...end.placed]
  return {
    placed,
    wires: flow.wires,
    slots: flow.slots,
    entry: start.entry,
    aim: start.aim,
    exit: end.exit,
    bounds: enclose({ placed, slots: flow.slots, wires: flow.wires, extra: [start.entry, end.exit] }),
  }
}
