import { useEffect, useRef, useState } from "react"
import * as Blockly from "blockly/core"
import * as blocklyEn from "blockly/msg/en"
import * as blocklyEs from "blockly/msg/es"

import { translate, useLocale } from "../i18n"
import { defineTrazaBlocks } from "./blocks"
import { labToolbox } from "./toolbox"

export function BlockWorkspace({
  onCount,
  onState,
  activeBlockId = null,
  allowed = null,
  restore = null,
  onLoadError = null,
  readOnly = false,
}: {
  onCount: (count: number) => void
  onState: (state: object) => void
  activeBlockId?: string | null
  allowed?: readonly string[] | null
  restore?: { key: number; state: object } | null
  onLoadError?: ((message: string) => void) | null
  readOnly?: boolean
}) {
  const locale = useLocale()
  const host = useRef<HTMLDivElement>(null)
  const workspaceRef = useRef<Blockly.WorkspaceSvg | null>(null)
  const snapshotRef = useRef<object | null>(null)
  const report = useRef(onCount)
  const reportState = useRef(onState)
  report.current = onCount
  reportState.current = onState

  const allowedKey = allowed ? allowed.join(",") : ""
  const [compact, setCompact] = useState(() => window.matchMedia("(max-width: 900px)").matches)
  useEffect(() => {
    const query = window.matchMedia("(max-width: 900px)")
    const onChange = () => setCompact(query.matches)
    query.addEventListener("change", onChange)
    return () => query.removeEventListener("change", onChange)
  }, [])
  const restoreRef = useRef(restore)
  restoreRef.current = restore
  const restoreKey = restore?.key ?? 0
  const reportError = useRef(onLoadError)
  reportError.current = onLoadError

  useEffect(() => {
    const node = host.current
    if (!node) return
    Blockly.setLocale((locale === "en" ? blocklyEn : blocklyEs) as unknown as { [key: string]: string })
    defineTrazaBlocks(locale)
    const workspace = Blockly.inject(node, {
      readOnly,
      toolbox: readOnly ? undefined : labToolbox(allowedKey ? allowedKey.split(",") : null, (key) => translate(locale, key)),
      renderer: "zelos",
      horizontalLayout: compact,
      toolboxPosition: compact ? "end" : "start",
      media: "/blockly-media/",
      trashcan: !readOnly,
      sounds: false,
      zoom: { controls: true, wheel: true, startScale: compact ? 0.8 : 1 },
      move: { scrollbars: true, drag: !readOnly, wheel: false },
      grid: { spacing: 24, length: 1, colour: "#e4e7ee", snap: true },
    })
    const saved = snapshotRef.current
    if (saved) {
      Blockly.serialization.workspaces.load(saved, workspace)
    }
    const publish = () => {
      report.current(workspace.getAllBlocks(false).length)
      reportState.current(Blockly.serialization.workspaces.save(workspace))
    }
    workspace.addChangeListener((event: Blockly.Events.Abstract) => {
      if (event.isUiEvent) return
      publish()
    })
    publish()
    workspaceRef.current = workspace
    Blockly.svgResize(workspace)
    const onResize = () => Blockly.svgResize(workspace)
    window.addEventListener("resize", onResize)
    const observer = new ResizeObserver(onResize)
    observer.observe(node)
    return () => {
      snapshotRef.current = Blockly.serialization.workspaces.save(workspace)
      observer.disconnect()
      window.removeEventListener("resize", onResize)
      workspaceRef.current = null
      workspace.dispose()
      node.replaceChildren()
    }
  }, [allowedKey, compact, locale, readOnly])

  useEffect(() => {
    const workspace = workspaceRef.current
    const request = restoreRef.current
    if (!workspace || !request || request.key !== restoreKey) return
    defineTrazaBlocks(locale)
    Blockly.Events.disable()
    try {
      workspace.clear()
      Blockly.serialization.workspaces.load(
        request.state as ReturnType<typeof Blockly.serialization.workspaces.save>,
        workspace,
      )
    } catch (caught) {
      console.error(caught)
      workspace.clear()
      reportError.current?.(translate(locale, "canvasLoadError"))
    } finally {
      Blockly.Events.enable()
    }
    report.current(workspace.getAllBlocks(false).length)
    reportState.current(Blockly.serialization.workspaces.save(workspace))
  }, [locale, restoreKey])

  useEffect(() => {
    const workspace = workspaceRef.current
    if (!workspace) return
    const block = activeBlockId ? workspace.getBlockById(activeBlockId) : null
    workspace.highlightBlock(block ? activeBlockId : null)
  }, [activeBlockId])

  return <div ref={host} className="lab-canvas" role="region" aria-label={translate(locale, "blockCanvas")} />
}
