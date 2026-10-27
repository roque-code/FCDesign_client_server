import type { LabPath, LabPathChallenge } from "../api"

export type SeenMark = {
  state: LabPathChallenge["state"]
  withdrawn: boolean
}

export type ChallengeNotice = {
  id: string
  pathId: string
  pathName: string
  title: string
  kind: "new" | "enabled"
}

type Listed = ChallengeNotice & SeenMark

export function noticeDiff(
  seen: Record<string, SeenMark> | null,
  paths: LabPath[],
): { notices: ChallengeNotice[]; seen: Record<string, SeenMark> } {
  const current = indexPaths(paths)
  if (seen === null) return { notices: [], seen: marksOf(current) }
  const next: Record<string, SeenMark> = { ...seen }
  const notices: ChallengeNotice[] = []
  for (const item of current.values()) {
    const previous = seen[item.id]
    if (!previous) {
      if (item.state !== "completed") {
        notices.push(noticeOf(item, "new"))
        delete next[item.id]
      } else {
        next[item.id] = markOf(item)
      }
      continue
    }
    const enabled =
      item.state !== "completed" &&
      ((previous.withdrawn && !item.withdrawn) ||
        (previous.state === "scheduled" && item.state === "available") ||
        (previous.state === "closed" && item.state === "available"))
    if (enabled) {
      notices.push(noticeOf(item, "enabled"))
      next[item.id] = previous
    } else {
      next[item.id] = markOf(item)
    }
  }
  for (const [id, mark] of Object.entries(seen)) {
    if (!current.has(id) && !mark.withdrawn) next[id] = { ...mark, withdrawn: true }
  }
  return { notices, seen: next }
}

export function acknowledge(paths: LabPath[], seen: Record<string, SeenMark>): Record<string, SeenMark> {
  const next = marksOf(indexPaths(paths))
  for (const [id, mark] of Object.entries(seen)) {
    if (!(id in next)) next[id] = { ...mark, withdrawn: true }
  }
  return next
}

function indexPaths(paths: LabPath[]): Map<string, Listed> {
  const current = new Map<string, Listed>()
  for (const path of paths) {
    for (const item of path.challenges) {
      if (current.has(item.id)) continue
      current.set(item.id, {
        id: item.id,
        pathId: path.id,
        pathName: path.name,
        title: item.title,
        kind: "new",
        state: item.state,
        withdrawn: item.withdrawn === true,
      })
    }
  }
  return current
}

function marksOf(current: Map<string, Listed>): Record<string, SeenMark> {
  const seen: Record<string, SeenMark> = {}
  for (const item of current.values()) seen[item.id] = markOf(item)
  return seen
}

function markOf(item: Listed): SeenMark {
  return { state: item.state, withdrawn: item.withdrawn }
}

function noticeOf(item: Listed, kind: ChallengeNotice["kind"]): ChallengeNotice {
  return { id: item.id, pathId: item.pathId, pathName: item.pathName, title: item.title, kind }
}
