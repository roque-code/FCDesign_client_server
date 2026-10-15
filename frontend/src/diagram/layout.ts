import type { FlowEdge, FlowGraph, FlowNode } from "../api"
import { spellText, type Dialect } from "../dialect"
import { backEdgeIndexes, collapseJoins, flowLabel, shownFigure } from "./figures"
import { measure } from "./measure"
import type { Drawing, DrawnEdge, DrawnNode, Point } from "./svg"

const GAP_X = 84
const GAP_Y = 52
const LANE = 48
const SIDE_GAP = 40

type Lane = { source: string; label: string | null; x: number }

type Item =
  | { kind: "node"; id: string }
  | { kind: "loop"; id: string; mode: "pre" | "post"; body: Item[]; exitLabel: string | null }
  | { kind: "branch"; id: string; arms: Array<{ label: string | null; body: Item[] }> }

type Box = { width: number; height: number; axis: number }

export async function layoutGraph(graph: FlowGraph, locale: Dialect = "es"): Promise<Drawing> {
  const nodes =
    locale === "es" ? graph.nodes : graph.nodes.map((node) => ({ ...node, text: spellText(locale, node.text) }))
  const visible = collapseJoins(nodes, graph.edges)
  const drawing = arrange(visible.nodes, visible.edges, graph.entry, locale)
  return frame(drawing.nodes, drawing.edges)
}

function arrange(flowNodes: FlowNode[], flowEdges: FlowEdge[], entry: string, locale: Dialect): Drawing {
  const sizes = new Map(flowNodes.map((node) => [node.id, measure(shownFigure(node), node.text)]))
  const byId = new Map(flowNodes.map((node) => [node.id, node]))
  const outgoing = new Map<string, FlowEdge[]>()
  const incoming = new Map<string, FlowEdge[]>()
  flowEdges.forEach((edge) => {
    const from = outgoing.get(edge.source) ?? []
    from.push(edge)
    outgoing.set(edge.source, from)
    const to = incoming.get(edge.target) ?? []
    to.push(edge)
    incoming.set(edge.target, to)
  })
  const backs = backEdgeIndexes(flowEdges)
  const backEdges = new Set([...backs].map((index) => flowEdges[index]))
  const preHeaders = new Set<string>()
  const postStart = new Map<string, string>()
  for (const edge of backEdges) {
    const sourceLoop = shownFigure(byId.get(edge.source) ?? flowNodes[0]) === "loop"
    if (edge.source === edge.target || shownFigure(byId.get(edge.target) ?? flowNodes[0]) === "loop") {
      preHeaders.add(edge.target)
    } else if (sourceLoop) {
      postStart.set(edge.target, edge.source)
    } else {
      preHeaders.add(edge.target)
    }
  }
  const forward = (id: string) => (outgoing.get(id) ?? []).filter((edge) => !backEdges.has(edge))

  function reachable(start: string, forbidden: Set<string>): Map<string, number> {
    const distance = new Map<string, number>()
    const queue = [start]
    distance.set(start, 0)
    while (queue.length > 0) {
      const id = queue.shift()
      if (!id || forbidden.has(id)) continue
      for (const edge of forward(id)) {
        if (distance.has(edge.target)) continue
        distance.set(edge.target, (distance.get(id) ?? 0) + 1)
        queue.push(edge.target)
      }
    }
    return distance
  }

  function findMerge(origin: string, targets: string[]): string | null {
    const maps = targets.map((target) => reachable(target, new Set([origin])))
    let best: string | null = null
    let bestDepth = Infinity
    for (const id of maps[0].keys()) {
      if (!maps.every((item) => item.has(id))) continue
      const depth = Math.max(...maps.map((item) => item.get(id) ?? 0))
      if (depth < bestDepth) {
        bestDepth = depth
        best = id
      }
    }
    return best
  }

  function parse(start: string, stop: Set<string>): Item[] {
    const items: Item[] = []
    let cursor: string | null = start
    const seen = new Set<string>()
    while (cursor && !stop.has(cursor) && !seen.has(cursor)) {
      seen.add(cursor)
      const postHeader = postStart.get(cursor)
      if (postHeader && !stop.has(postHeader)) {
        const body = parse(cursor, new Set([...stop, postHeader]))
        const exit = forward(postHeader).find((edge) => edge.label === "Sí") ?? forward(postHeader)[0]
        items.push({ kind: "loop", id: postHeader, mode: "post", body, exitLabel: null })
        cursor = exit?.target && !stop.has(exit.target) ? exit.target : null
        continue
      }
      if (preHeaders.has(cursor)) {
        const outs = forward(cursor)
        const exit = outs.find((edge) => edge.label === "No") ?? outs.find((edge) => edge.label !== "Sí")
        const bodyEdge = outs.find((edge) => edge !== exit && edge.target !== cursor)
        const body = bodyEdge ? parse(bodyEdge.target, new Set([...stop, cursor])) : []
        items.push({ kind: "loop", id: cursor, mode: "pre", body, exitLabel: exit?.label ?? "No" })
        cursor = exit?.target && !stop.has(exit.target) ? exit.target : null
        continue
      }
      const outs = forward(cursor)
      if (outs.length <= 1) {
        items.push({ kind: "node", id: cursor })
        cursor = outs[0]?.target ?? null
        continue
      }
      const merge = findMerge(cursor, outs.map((edge) => edge.target))
      const stops = new Set(stop)
      if (merge) stops.add(merge)
      const ordered = isSwitch(cursor) ? [...outs] : [...outs].sort((left, right) => armRank(left.label) - armRank(right.label))
      const arms = ordered.map((edge) => ({
          label: edge.label,
          body: !merge || edge.target !== merge ? parse(edge.target, stops) : [],
        }))
      items.push({ kind: "branch", id: cursor, arms })
      cursor = merge && !stop.has(merge) ? merge : null
    }
    return items
  }

  const positions = new Map<string, { x: number; y: number }>()
  const lanes: Lane[] = []
  const switchCases = new Map<string, Array<{ label: string | null; offset: number; width: number }>>()

  function isSwitch(id: string): boolean {
    const node = byId.get(id)
    return node !== undefined && shownFigure(node) === "switch"
  }

  function metrics(item: Item): Box {
    if (item.kind === "node") {
      const size = sizes.get(item.id) ?? { width: 132, height: 44 }
      return { width: size.width, height: size.height, axis: size.width / 2 }
    }
    if (item.kind === "loop") return loopBox(item)
    return branchBox(item)
  }

  function loopBox(item: Extract<Item, { kind: "loop" }>): Box {
    const header = sizes.get(item.id) ?? { width: 168, height: 72 }
    const body = metricsSeq(item.body)
    if (item.mode === "post") {
      const axis = Math.max(body.axis, header.width / 2)
      const right = Math.max(body.width - body.axis, header.width / 2) + 40
      const height = (body.height > 0 ? body.height + GAP_Y : 0) + header.height
      return { width: axis + right, height, axis }
    }
    const width = header.width + (body.width > 0 ? GAP_X + body.width : 0) + 40
    const stacked = body.height > 0 ? GAP_Y + body.height : 0
    return { width, height: header.height + stacked, axis: header.width / 2 }
  }

  function branchLayout(item: Extract<Item, { kind: "branch" }>) {
    const diamond = sizes.get(item.id) ?? { width: 168, height: 96 }
    const slots = item.arms.map((arm) => {
      const box = metricsSeq(arm.body)
      const empty = arm.body.length === 0
      return { label: arm.label, body: arm.body, width: empty ? LANE : box.width, empty, height: box.height, rank: armRank(arm.label) }
    })
    const leftSlots = slots.filter((slot) => slot.rank === 0)
    const rightSlots = slots.filter((slot) => slot.rank === 2)
    const midSlots = slots.filter((slot) => slot.rank !== 0 && slot.rank !== 2)
    const span = (group: typeof slots) =>
      group.reduce((sum, slot) => sum + slot.width, 0) + GAP_X * Math.max(0, group.length - 1)
    const leftSpan = span(leftSlots)
    const rightSpan = span(rightSlots)
    const midSpan = span(midSlots)
    const leftWidth = leftSpan > 0 ? leftSpan + SIDE_GAP : 0
    const rightWidth = rightSpan > 0 ? rightSpan + SIDE_GAP : 0
    const midOverflow = Math.max(0, (midSpan - diamond.width) / 2)
    const tall = Math.max(0, ...slots.map((slot) => (slot.empty ? 0 : slot.height)))
    return {
      width: leftWidth + midOverflow + diamond.width + midOverflow + rightWidth,
      height: diamond.height + (tall > 0 ? GAP_Y + tall : 0),
      axis: leftWidth + midOverflow + diamond.width / 2,
      diamond,
      leftSlots,
      rightSlots,
      midSlots,
      leftSpan,
      rightSpan,
      midSpan,
    }
  }

  function switchLayout(item: Extract<Item, { kind: "branch" }>) {
    const slots = item.arms.map((arm) => {
      const box = metricsSeq(arm.body)
      const empty = arm.body.length === 0
      const text = spellText(locale, arm.label ?? "De Otro Modo")
      const labelWidth = Math.ceil(text.length * 7.2 + 28)
      const width = Math.max(92, labelWidth, empty ? 0 : box.width + 36)
      return { label: arm.label, body: arm.body, width, empty, height: box.height }
    })
    const width = Math.max(1, slots.reduce((sum, slot) => sum + slot.width, 0))
    const nodeHeight = 100
    sizes.set(item.id, { width, height: nodeHeight })
    const tall = Math.max(0, ...slots.map((slot) => (slot.empty ? 0 : slot.height)))
    return {
      width,
      height: nodeHeight + (tall > 0 ? GAP_Y + tall : 0),
      axis: width / 2,
      nodeHeight,
      slots,
    }
  }

  function branchBox(item: Extract<Item, { kind: "branch" }>): Box {
    if (isSwitch(item.id)) {
      const layout = switchLayout(item)
      return { width: layout.width, height: layout.height, axis: layout.axis }
    }
    const layout = branchLayout(item)
    return { width: layout.width, height: layout.height, axis: layout.axis }
  }

  function metricsSeq(items: Item[]): Box {
    if (items.length === 0) return { width: 0, height: 0, axis: 0 }
    const parts = items.map(metrics)
    const axis = Math.max(...parts.map((part) => part.axis))
    const right = Math.max(...parts.map((part) => part.width - part.axis))
    const height = parts.reduce((sum, part) => sum + part.height, 0) + GAP_Y * (parts.length - 1)
    return { width: axis + right, height, axis }
  }

  function placeSeq(items: Item[], left: number, top: number) {
    if (items.length === 0) return
    const box = metricsSeq(items)
    let y = top
    for (const item of items) {
      const part = metrics(item)
      place(item, left + box.axis - part.axis, y)
      y += part.height + GAP_Y
    }
  }

  function place(item: Item, left: number, top: number) {
    if (item.kind === "node") {
      positions.set(item.id, { x: left, y: top })
      return
    }
    if (item.kind === "loop") {
      placeLoop(item, left, top)
      return
    }
    placeBranch(item, left, top)
  }

  function placeLoop(item: Extract<Item, { kind: "loop" }>, left: number, top: number) {
    const header = sizes.get(item.id) ?? { width: 168, height: 72 }
    const body = metricsSeq(item.body)
    if (item.mode === "post") {
      const box = loopBox(item)
      placeSeq(item.body, left + box.axis - body.axis, top)
      const bodyHeight = body.height > 0 ? body.height + GAP_Y : 0
      positions.set(item.id, { x: left + box.axis - header.width / 2, y: top + bodyHeight })
      return
    }
    positions.set(item.id, { x: left, y: top })
    placeSeq(item.body, left + header.width + GAP_X, top + header.height + GAP_Y)
  }

  function placeSwitch(item: Extract<Item, { kind: "branch" }>, left: number, top: number) {
    const layout = switchLayout(item)
    positions.set(item.id, { x: left, y: top })
    const contentTop = top + layout.nodeHeight + GAP_Y
    let x = left
    const cases: Array<{ label: string | null; offset: number; width: number }> = []
    for (const slot of layout.slots) {
      if (!slot.empty) {
        const box = metricsSeq(slot.body)
        placeSeq(slot.body, x + slot.width / 2 - box.axis, contentTop)
      }
      cases.push({ label: slot.label, offset: x - left, width: slot.width })
      x += slot.width
    }
    switchCases.set(item.id, cases)
  }

  function placeBranch(item: Extract<Item, { kind: "branch" }>, left: number, top: number) {
    if (isSwitch(item.id)) {
      placeSwitch(item, left, top)
      return
    }
    const layout = branchLayout(item)
    const diamondX = left + layout.axis - layout.diamond.width / 2
    positions.set(item.id, { x: diamondX, y: top })
    const contentTop = top + layout.diamond.height + GAP_Y
    const placeGroup = (group: typeof layout.leftSlots, start: number) => {
      let x = start
      for (const slot of group) {
        if (slot.empty) lanes.push({ source: item.id, label: slot.label, x: x + slot.width / 2 })
        else placeSeq(slot.body, x, contentTop)
        x += slot.width + GAP_X
      }
    }
    placeGroup(layout.leftSlots, diamondX - SIDE_GAP - layout.leftSpan)
    placeGroup(layout.rightSlots, diamondX + layout.diamond.width + SIDE_GAP)
    placeGroup(layout.midSlots, diamondX + layout.diamond.width / 2 - layout.midSpan / 2)
  }

  const drawn: DrawnNode[] = []
  const covered = new Set<string>()
  let cursorY = 0
  const starts = [entry, ...flowNodes.filter((node) => (incoming.get(node.id) ?? []).length === 0 && node.id !== entry).map((node) => node.id)]
  for (const start of starts) {
    if (covered.has(start)) continue
    const items = parse(start, new Set())
    placeSeq(items, 0, cursorY)
    const box = metricsSeq(items)
    cursorY += box.height + GAP_Y * 2
    for (const [id] of positions) covered.add(id)
  }
  for (const node of flowNodes) {
    if (positions.has(node.id)) continue
    positions.set(node.id, { x: 0, y: cursorY })
    cursorY += (sizes.get(node.id)?.height ?? 44) + GAP_Y
  }
  for (const node of flowNodes) {
    const size = sizes.get(node.id) ?? { width: 132, height: 44 }
    const at = positions.get(node.id) ?? { x: 0, y: 0 }
    drawn.push({
      id: node.id,
      kind: node.kind,
      figure: shownFigure(node),
      text: node.text,
      line: node.line,
      x: at.x,
      y: at.y,
      width: size.width,
      height: size.height,
      cases: switchCases.get(node.id),
    })
  }
  const nodes = new Map(drawn.map((node) => [node.id, node]))
  const used: Segment[] = []
  const edges: DrawnEdge[] = flowEdges.map((edge) => {
    const points = route(edge, nodes, backEdges.has(edge), lanes, used)
    remember(points, used)
    return {
      source: edge.source,
      target: edge.target,
      label: nodes.get(edge.source)?.figure === "switch" ? null : flowLabel(edge.label, locale),
      points,
    }
  })
  return { nodes: drawn, edges, width: 0, height: 0 }
}

function armRank(label: string | null): number {
  if (label === "No" || label === "De Otro Modo") return 0
  if (label === "Sí") return 2
  return 1
}

function branchSide(label: string | null): "left" | "right" | null {
  if (label === "Sí") return "right"
  if (label === "No" || label === "De Otro Modo") return "left"
  return null
}

function exitPoint(source: DrawnNode, side: "left" | "right"): Point {
  return { x: side === "left" ? source.x : source.x + source.width, y: source.y + source.height / 2 }
}

type Segment = { x1: number; y1: number; x2: number; y2: number }

function spanRoute(
  source: DrawnNode,
  target: DrawnNode,
  side: "left" | "right",
  nodes: Map<string, DrawnNode>,
  laneX?: number,
  outward = 0,
): Point[] {
  const exit = exitPoint(source, side)
  const targetX = target.x + target.width / 2
  let bound = side === "left" ? source.x : source.x + source.width
  let bottom = source.y + source.height
  for (const node of nodes.values()) {
    if (node.id === source.id || node.id === target.id) continue
    if (node.y + node.height <= exit.y) continue
    if (node.y >= target.y - 2) continue
    bottom = Math.max(bottom, node.y + node.height)
    if (side === "left") bound = Math.min(bound, node.x)
    else bound = Math.max(bound, node.x + node.width)
  }
  const base =
    side === "left"
      ? Math.min(laneX ?? bound - 20, source.x - 16, bound - 16)
      : Math.max(laneX ?? bound + 20, source.x + source.width + 16, bound + 16)
  const rail = side === "left" ? base - outward : base + outward
  const low = bottom + 16
  const high = Math.max(low, target.y - 18)
  const bus = Math.max(low, high - Math.min(outward, 12))
  return [exit, { x: rail, y: exit.y }, { x: rail, y: bus }, { x: targetX, y: bus }, { x: targetX, y: target.y }]
}

function topOf(target: DrawnNode): Point {
  return { x: target.x + target.width / 2, y: target.y }
}

function arriveTop(from: Point, target: DrawnNode, outward: boolean): Point[] {
  const to = topOf(target)
  const above = { x: to.x, y: to.y - 16 }
  if (from.y <= above.y) return [from, { x: to.x, y: from.y }, above, to]
  const step = outward ? from.x - 20 : from.x + 20
  return [from, { x: step, y: from.y }, { x: step, y: above.y }, above, to]
}

function sideOptions(source: DrawnNode, target: DrawnNode, side: "left" | "right", laneX?: number): Point[][] {
  const exit = exitPoint(source, side)
  const targetX = target.x + target.width / 2
  const outward = side === "left"
  const paths: Point[][] = []
  const columnOutside = outward ? targetX <= source.x + 1 : targetX >= source.x + source.width - 1
  if (target.y >= source.y + source.height - 4 && columnOutside) {
    paths.push([exit, { x: targetX, y: exit.y }, { x: targetX, y: target.y }])
  }
  if (target.y >= source.y + source.height - 4) {
    const outX = outward ? exit.x - 20 : exit.x + 20
    const turn = Math.min(source.y + source.height + 16, target.y - 16)
    if (turn > exit.y + 4 && turn < target.y) {
      paths.push([
        exit,
        { x: outX, y: exit.y },
        { x: outX, y: turn },
        { x: targetX, y: turn },
        { x: targetX, y: target.y },
      ])
    }
  }
  paths.push(arriveTop(exit, target, outward))
  const rail = outward
    ? Math.min(laneX ?? source.x - 28, source.x - 16)
    : Math.max(laneX ?? source.x + source.width + 28, source.x + source.width + 16)
  if (target.y > exit.y) {
    const bus = Math.max(source.y + source.height + 18, target.y - 18)
    paths.push([exit, { x: rail, y: exit.y }, { x: rail, y: bus }, { x: targetX, y: bus }, { x: targetX, y: target.y }])
  }
  return paths
}

function route(
  edge: FlowEdge,
  nodes: Map<string, DrawnNode>,
  returning: boolean,
  lanes: Lane[] = [],
  used: Segment[] = [],
): Point[] {
  const source = nodes.get(edge.source)
  const target = nodes.get(edge.target)
  if (!source || !target) return []
  if (source.figure === "switch") return switchRoute(source, target, edge.label, nodes)
  const side = branchSide(edge.label)
  if (source.id === target.id) return selfLoop(source, side)
  if (side && (source.figure === "decision" || source.figure === "loop")) {
    const lane = lanes.find((item) => item.source === edge.source && item.label === edge.label)
    if (source.figure === "loop" && side === "right" && target.y >= source.y + source.height - 4) {
      const intoBody = loopBodyRoute(source, target)
      if (!crosses(intoBody, nodes, source.id, target.id) && !joins(intoBody, used)) return intoBody
    }
    if (source.figure === "loop" && side === "left" && target.y + target.height <= source.y + 4) {
      return (
        clearOf(used, (outward) => postFalseRoute(source, target, nodes, outward), nodes, source.id, target.id) ??
        postFalseRoute(source, target, nodes, 0)
      )
    }
    if (target.y >= source.y + source.height - 4) {
      const around = clearOf(used, (outward) => spanRoute(source, target, side, nodes, lane?.x, outward), nodes, source.id, target.id)
      if (around) return around
    }
    const options = sideOptions(source, target, side, lane?.x)
    for (const path of options) {
      if (!crosses(path, nodes, source.id, target.id) && !joins(path, used)) return path
    }
    return options[options.length - 1]
  }
  if (returning || target.y + target.height <= source.y + 4) {
    return clearOf(used, (outward) => returnRoute(source, target, nodes, outward), nodes, source.id, target.id) ?? returnRoute(source, target, nodes, 0)
  }
  if (source.figure === "decision" || source.figure === "loop") {
    if (overlapsY(source, target) && target.x + target.width <= source.x) {
      const path = sideRoute(source, target, true)
      if (!crosses(path, nodes, source.id, target.id)) return path
    }
    if (overlapsY(source, target) && target.x >= source.x + source.width - 4) {
      const path = sideRoute(source, target, false)
      if (!crosses(path, nodes, source.id, target.id)) return path
    }
    const gap = target.y - (source.y + source.height)
    const offset = Math.abs(target.x + target.width / 2 - (source.x + source.width / 2))
    if (offset > 8 && gap >= 0 && gap <= GAP_Y + 8) {
      const drop = dropIntoColumn(source, target)
      if (!crosses(drop, nodes, source.id, target.id)) return drop
    }
  }
  const down = downThenAcross(source, target)
  if (!crosses(down, nodes, source.id, target.id)) return down
  const across = acrossThenDown(source, target)
  if (!crosses(across, nodes, source.id, target.id)) return across
  return down
}

function overlapsY(source: DrawnNode, target: DrawnNode): boolean {
  return source.y < target.y + target.height && target.y < source.y + source.height
}

function switchRoute(source: DrawnNode, target: DrawnNode, label: string | null, nodes: Map<string, DrawnNode>): Point[] {
  const slot = source.cases?.find((item) => item.label === label)
  const exitX = slot ? source.x + slot.offset + slot.width / 2 : source.x + source.width / 2
  const from = { x: exitX, y: source.y + source.height }
  const to = { x: target.x + target.width / 2, y: target.y }
  const straight = [from, to]
  if (Math.abs(from.x - to.x) < 8 && to.y >= from.y && !crosses(straight, nodes, source.id, target.id)) return straight
  let floor = from.y
  const minX = Math.min(from.x, to.x)
  const maxX = Math.max(from.x, to.x)
  for (const node of nodes.values()) {
    if (node.id === source.id || node.id === target.id) continue
    if (node.y + node.height <= from.y + 4 || node.y >= to.y - 4) continue
    if (node.x + node.width < minX - 4 || node.x > maxX + 4) continue
    floor = Math.max(floor, node.y + node.height)
  }
  const low = Math.max(floor + 16, from.y + 16)
  const bus = Math.max(low, to.y - 18) < to.y - 8 ? Math.max(low, to.y - 18) : low
  return [from, { x: from.x, y: bus }, { x: to.x, y: bus }, to]
}

function postFalseRoute(source: DrawnNode, target: DrawnNode, nodes: Map<string, DrawnNode>, outward = 0): Point[] {
  const exit = exitPoint(source, "left")
  const into = topOf(target)
  const top = target.y
  const bottom = source.y + source.height
  let left = Math.min(source.x, target.x)
  for (const node of nodes.values()) {
    if (node.id === source.id || node.id === target.id) continue
    if (node.y + node.height <= top + 4) continue
    if (node.y >= bottom - 4) continue
    left = Math.min(left, node.x)
  }
  const rail = left - 32 - outward
  const approach = into.y - 16
  return [exit, { x: rail, y: exit.y }, { x: rail, y: approach }, { x: into.x, y: approach }, into]
}

function loopBodyRoute(source: DrawnNode, target: DrawnNode): Point[] {
  const exit = exitPoint(source, "right")
  const to = topOf(target)
  const out = exit.x + 22
  const under = source.y + source.height + 18
  const turn = Math.min(under, to.y - 16)
  return [exit, { x: out, y: exit.y }, { x: out, y: turn }, { x: to.x, y: turn }, to]
}

function sideRoute(source: DrawnNode, target: DrawnNode, toLeft: boolean): Point[] {
  const from = { x: toLeft ? source.x : source.x + source.width, y: source.y + source.height / 2 }
  return arriveTop(from, target, toLeft)
}

function downThenAcross(source: DrawnNode, target: DrawnNode): Point[] {
  const from = { x: source.x + source.width / 2, y: source.y + source.height }
  const to = { x: target.x + target.width / 2, y: target.y }
  if (Math.abs(from.x - to.x) < 6) return [from, to]
  const bus = Math.max(from.y + 18, to.y - 18)
  return [from, { x: from.x, y: bus }, { x: to.x, y: bus }, to]
}

function dropIntoColumn(source: DrawnNode, target: DrawnNode): Point[] {
  const targetX = target.x + target.width / 2
  const toLeft = targetX < source.x + source.width / 2
  const underDiamond = targetX > source.x + 8 && targetX < source.x + source.width - 8
  if (underDiamond) return acrossThenDown(source, target)
  const y = source.y + source.height / 2
  const x = toLeft ? source.x : source.x + source.width
  return [
    { x, y },
    { x: targetX, y },
    { x: targetX, y: target.y },
  ]
}

function acrossThenDown(source: DrawnNode, target: DrawnNode): Point[] {
  const from = { x: source.x + source.width / 2, y: source.y + source.height }
  const to = { x: target.x + target.width / 2, y: target.y }
  const bus = from.y + 18
  return [from, { x: from.x, y: bus }, { x: to.x, y: bus }, to]
}

function returnRoute(source: DrawnNode, target: DrawnNode, nodes: Map<string, DrawnNode>, outward = 0): Point[] {
  const top = Math.min(source.y, target.y)
  const bottom = Math.max(source.y + source.height, target.y + target.height)
  let right = Math.max(source.x + source.width, target.x + target.width)
  for (const node of nodes.values()) {
    if (node.id === source.id || node.id === target.id) continue
    if (node.y >= bottom || node.y + node.height <= top) continue
    right = Math.max(right, node.x + node.width)
  }
  const channel = right + 32 + outward
  const drop = 16 + Math.min(outward, 18)
  const from = { x: source.x + source.width / 2, y: source.y + source.height }
  const into = topOf(target)
  const approach = into.y - 16
  const high = approach - 28 - outward
  const lane = target.x + target.width + 24
  return [
    from,
    { x: from.x, y: from.y + drop },
    { x: channel, y: from.y + drop },
    { x: channel, y: high },
    { x: lane, y: high },
    { x: lane, y: approach },
    { x: into.x, y: approach },
    into,
  ]
}

function clearOf(
  used: Segment[],
  build: (outward: number) => Point[],
  nodes: Map<string, DrawnNode>,
  source: string,
  target: string,
): Point[] | null {
  for (let step = 0; step < 6; step += 1) {
    const path = build(step * 22)
    if (!crosses(path, nodes, source, target) && !joins(path, used)) return path
  }
  return null
}

function remember(points: Point[], used: Segment[]) {
  for (let index = 0; index < points.length - 1; index += 1) {
    const from = points[index]
    const to = points[index + 1]
    if (Math.hypot(to.x - from.x, to.y - from.y) < 24) continue
    used.push({ x1: from.x, y1: from.y, x2: to.x, y2: to.y })
  }
}

function joins(points: Point[], used: Segment[]): boolean {
  for (let index = 0; index < points.length - 1; index += 1) {
    const from = points[index]
    const to = points[index + 1]
    if (Math.hypot(to.x - from.x, to.y - from.y) < 24) continue
    const vertical = Math.abs(from.x - to.x) < 1
    for (const other of used) {
      const otherVertical = Math.abs(other.x1 - other.x2) < 1
      if (vertical && otherVertical && Math.abs(from.x - other.x1) < 12 && shares(from.y, to.y, other.y1, other.y2)) return true
      if (!vertical && !otherVertical && Math.abs(from.y - other.y1) < 12 && shares(from.x, to.x, other.x1, other.x2)) return true
    }
  }
  return false
}

function shares(a1: number, a2: number, b1: number, b2: number): boolean {
  const start = Math.max(Math.min(a1, a2), Math.min(b1, b2))
  const end = Math.min(Math.max(a1, a2), Math.max(b1, b2))
  return end - start > 10
}

function selfLoop(node: DrawnNode, side: "left" | "right" | null = null): Point[] {
  const leaveRight = side !== "left"
  const from = { x: leaveRight ? node.x + node.width : node.x, y: node.y + node.height / 2 }
  const channel = leaveRight ? from.x + 32 : from.x - 32
  return [from, { x: channel, y: from.y }, { x: channel, y: node.y - 16 }, { x: node.x + node.width / 2, y: node.y - 16 }, { x: node.x + node.width / 2, y: node.y }]
}

function crosses(points: Point[], nodes: Map<string, DrawnNode>, source: string, target: string): boolean {
  for (let index = 0; index < points.length - 1; index += 1) {
    const from = points[index]
    const to = points[index + 1]
    for (const node of nodes.values()) {
      if (node.id === source || node.id === target) continue
      if (segmentHits(from, to, node)) return true
    }
  }
  return false
}

function segmentHits(from: Point, to: Point, node: DrawnNode): boolean {
  const left = node.x + 6
  const right = node.x + node.width - 6
  const top = node.y + 6
  const bottom = node.y + node.height - 6
  if (right <= left || bottom <= top) return false
  if (Math.abs(from.y - to.y) < 1) {
    const y = from.y
    const minX = Math.min(from.x, to.x)
    const maxX = Math.max(from.x, to.x)
    return y > top && y < bottom && maxX > left && minX < right
  }
  if (Math.abs(from.x - to.x) < 1) {
    const x = from.x
    const minY = Math.min(from.y, to.y)
    const maxY = Math.max(from.y, to.y)
    return x > left && x < right && maxY > top && minY < bottom
  }
  return false
}

function frame(nodes: DrawnNode[], edges: DrawnEdge[]): Drawing {
  let minX = 0
  let minY = 0
  let maxX = 48
  let maxY = 48
  const consider = (x: number, y: number) => {
    minX = Math.min(minX, x)
    minY = Math.min(minY, y)
    maxX = Math.max(maxX, x)
    maxY = Math.max(maxY, y)
  }
  for (const node of nodes) {
    consider(node.x, node.y)
    consider(node.x + node.width, node.y + node.height)
  }
  for (const edge of edges) for (const point of edge.points) consider(point.x, point.y)
  const shiftX = minX < 16 ? 16 - minX : 0
  const shiftY = minY < 16 ? 16 - minY : 0
  if (shiftX || shiftY) {
    for (const node of nodes) {
      node.x += shiftX
      node.y += shiftY
    }
    for (const edge of edges) {
      edge.points = edge.points.map((point) => ({ x: point.x + shiftX, y: point.y + shiftY }))
    }
  }
  return { nodes, edges, width: maxX + shiftX + 28, height: maxY + shiftY + 28 }
}
