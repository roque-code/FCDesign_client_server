import {
  ApiError,
  type Diagnostic,
  type Execution,
  type FlowGraph,
  type LabPreview,
  type LabRun,
  type TranslationResult,
} from "./api"
import { localMissingMessage } from "./i18n"

export type LocalEndpoint = {
  origin: string
  token: string
}

export type LanguageBody = {
  profile_key: string
  require_semicolons: boolean
  index_base: 0 | 1
}

type TrazaWindow = Window & {
  __TRAZA_LOCAL__?: { origin?: string; token?: string }
  __TRAZA_DESKTOP_PROXY__?: boolean
  __TRAZA_LAUNCH__?: string
  __TAURI_INTERNALS__?: { invoke: (command: string, args: Record<string, unknown>) => Promise<unknown> }
}

export function installedLocal(): LocalEndpoint | null {
  if (typeof window === "undefined") return null
  const value = (window as TrazaWindow).__TRAZA_LOCAL__
  if (!value || typeof value.origin !== "string" || !value.origin) return null
  if (typeof value.token !== "string" || !value.token) return null
  return { origin: value.origin.replace(/\/$/, ""), token: value.token }
}

export function inInstalledApp(): boolean {
  if (typeof window === "undefined") return false
  return installedLocal() !== null || "__TAURI_INTERNALS__" in window
}

export function desktopProxiesServer(): boolean {
  if (typeof window === "undefined") return false
  return (window as TrazaWindow).__TRAZA_DESKTOP_PROXY__ === true
}

export function editorEventUrl(id: string, local: LocalEndpoint | null = installedLocal()): string {
  if (!local) return `/api/v1/executions/${id}/events/`
  return localUrl(local, `/local/v1/sessions/${id}/events/`)
}

export function labEventUrl(id: string, local: LocalEndpoint | null = installedLocal()): string {
  if (!local) return `/api/v1/learning/runs/${id}/events/`
  return localUrl(local, `/local/v1/lab/runs/${id}/events/`)
}

export function openEditorEvents(id: string): EventSource {
  if (!inInstalledApp()) return new EventSource(`/api/v1/executions/${id}/events/`)
  const local = installedLocal()
  if (!local) throw new ApiError(0, "local_missing", localMissingMessage())
  return new EventSource(editorEventUrl(id, local))
}

export function openLabEvents(id: string): EventSource {
  if (!inInstalledApp()) return new EventSource(`/api/v1/learning/runs/${id}/events/`)
  const local = installedLocal()
  if (!local) throw new ApiError(0, "local_missing", localMissingMessage())
  return new EventSource(labEventUrl(id, local))
}

export function searchFromLaunch(current: string, launch: string | undefined): string {
  if (current.includes("confirmar=") || current.includes("restablecer=")) return current
  if (!launch) return current
  const mark = launch.indexOf("?")
  return mark >= 0 ? launch.slice(mark) : current
}

export function launchSearch(): string {
  if (typeof window === "undefined") return ""
  const launch = (window as TrazaWindow).__TRAZA_LAUNCH__
  return searchFromLaunch(window.location.search, launch)
}

export function localValidate(source: string, profile: LanguageBody): Promise<{ diagnostics: Diagnostic[] }> {
  return localJson("/local/v1/validate", { source, profile })
}

export function localTranslate(source: string, profile: LanguageBody): Promise<TranslationResult> {
  return localJson("/local/v1/translate", { source, profile })
}

export function localFlowchart(
  source: string,
  profile: LanguageBody,
): Promise<{ graph: FlowGraph | null; diagnostics: Diagnostic[] }> {
  return localJson("/local/v1/flowchart", { source, profile })
}

export function localExecute(source: string, profile: LanguageBody): Promise<Execution> {
  return localJson("/local/v1/sessions", { source, profile, breakpoints: [], interactive: false })
}

export function localDebug(source: string, profile: LanguageBody, breakpoints: number[]): Promise<Execution> {
  return localJson("/local/v1/sessions", { source, profile, breakpoints, interactive: true })
}

export function localControl(id: string, action: string, breakpoints?: number[]): Promise<Execution> {
  return localJson(`/local/v1/sessions/${id}/control`, breakpoints ? { action, breakpoints } : { action })
}

export function localInspect(id: string, name: string, start = 0, count = 24) {
  return localJson<{ name: string; start: number; total: number; lengths: number[]; base: number; values: string[] }>(
    `/local/v1/sessions/${id}/inspect`,
    { name, start, count },
  )
}

export function localInput(id: string, text: string): Promise<Execution> {
  return localJson(`/local/v1/sessions/${id}/input`, { text })
}

export function localExecution(id: string): Promise<Execution> {
  return localJson(`/local/v1/sessions/${id}`, undefined, "GET")
}

export function localPreview(workspace: object): Promise<LabPreview> {
  return localJson("/local/v1/lab/preview", { workspace })
}

export function localImport(source: string): Promise<{ workspace: object | null; diagnostics: Diagnostic[] }> {
  return localJson("/local/v1/lab/import", { source })
}

export function localStartLab(workspace: object): Promise<LabRun> {
  return localJson("/local/v1/lab/runs", { workspace })
}

export function localControlLab(id: string, action: string): Promise<LabRun> {
  return localJson(`/local/v1/lab/runs/${id}/control`, { action })
}

export function localInputLab(id: string, text: string): Promise<LabRun> {
  return localJson(`/local/v1/lab/runs/${id}/input`, { text })
}

export function localLabRun(id: string): Promise<LabRun> {
  return localJson(`/local/v1/lab/runs/${id}`, undefined, "GET")
}

export function rememberAccess(access: { features: Record<string, boolean> }): Promise<{ ok: boolean }> {
  return localJson("/local/v1/access", { access })
}

export type ForeignRun = {
  status: "ok" | "error" | "missing" | "waiting"
  via: "system" | "cached" | "missing"
  exit_code: number | null
  stdout: string
  stderr: string
  message: string
  session: string
}

export type ForeignStatus = {
  platform: string
  languages: { language: string; label: string; ready: boolean; via: "system" | "cached" | "missing" }[]
}

export function localForeignStatus(): Promise<ForeignStatus> {
  return localJson("/local/v1/foreign/status", {})
}

export function localForeignRun(language: string, source: string, stdin: string): Promise<ForeignRun> {
  return localJson("/local/v1/foreign/run", { language, source, stdin })
}

export function localForeignOpen(language: string, source: string): Promise<ForeignRun> {
  return localJson("/local/v1/foreign/open", { language, source })
}

export function localForeignInput(session: string, text: string): Promise<ForeignRun> {
  return localJson("/local/v1/foreign/input", { session, text })
}

export function localForeignPoll(session: string): Promise<ForeignRun> {
  return localJson("/local/v1/foreign/poll", { session })
}

export function localForeignClose(session: string): Promise<{ ok: boolean }> {
  return localJson("/local/v1/foreign/close", { session })
}

function localUrl(local: LocalEndpoint, path: string): string {
  const url = new URL(`${local.origin}${path}`)
  url.searchParams.set("token", local.token)
  return url.toString()
}

async function localJson<T>(path: string, body: unknown, method = "POST"): Promise<T> {
  const local = installedLocal()
  if (!local) {
    throw new ApiError(0, "local_missing", localMissingMessage())
  }
  const response = await fetch(localUrl(local, path), {
    method,
    headers: {
      Authorization: `Bearer ${local.token}`,
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  })
  const data = (await response.json()) as { error?: { code?: string; message?: string } }
  if (!response.ok) {
    const error = data.error ?? {}
    throw new ApiError(response.status, error.code ?? "invalid", error.message ?? "No se pudo completar la solicitud.")
  }
  return data as T
}
