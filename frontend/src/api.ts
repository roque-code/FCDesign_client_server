import { localMissingMessage } from "./i18n"

export type Role = "student" | "teacher"
export type AccountRole = Role | "admin"

export type AccountPlan = {
  code: string
  name: string
  audience: Role
  price_cents: number
  currency: string
  period_days: number
  status: "active" | "expired"
  paid_until: string | null
  days_remaining: number | null
}

export type AccountAccess = {
  browser_app: boolean
  features: Record<string, boolean>
  limits: { max_projects: number | null; max_algorithms: number | null }
}

export type Account = {
  id: number
  email: string
  display_name: string
  institution: string
  role: AccountRole
  points: number
  rank: number
  translation_enabled: boolean
  paste_enabled: boolean
  avatar: string | null
  plan: AccountPlan | null
  access: AccountAccess
  usage: { projects: number; algorithms: number }
}

export function accessOf(account: { access?: AccountAccess | null } | null | undefined): AccountAccess {
  const access = account?.access
  if (!access || typeof access !== "object") {
    return { browser_app: false, features: {}, limits: { max_projects: null, max_algorithms: null } }
  }
  const features = access.features && typeof access.features === "object" ? access.features : {}
  const limits = access.limits
  return {
    browser_app: access.browser_app === true,
    features,
    limits: {
      max_projects: typeof limits?.max_projects === "number" ? limits.max_projects : null,
      max_algorithms: typeof limits?.max_algorithms === "number" ? limits.max_algorithms : null,
    },
  }
}

export function asAccount(value: Account): Account {
  return {
    ...value,
    access: accessOf(value),
    usage: value.usage ?? { projects: 0, algorithms: 0 },
  }
}

export type PlanFeature = {
  key: string
  label: string
  audiences: Role[]
}

export type BillingPlan = {
  id: string
  code: string
  name: string
  audience: Role
  price_cents: number
  currency: string
  period_days: number
  browser_allowed: boolean
  max_projects: number | null
  max_algorithms: number | null
  features: Record<string, boolean>
  is_default: boolean
  is_active: boolean
  sort_order: number
}

export type BillingPlanInput = {
  code?: string
  name: string
  audience?: Role
  price_cents: number
  currency: string
  period_days: number
  browser_allowed: boolean
  max_projects: number | null
  max_algorithms: number | null
  features: Record<string, boolean>
  is_active?: boolean
}

export type Subscriber = {
  id: number
  email: string
  display_name: string
  role: AccountRole
  plan: AccountPlan | null
  browser_allowed: boolean | null
}

export type PendingConfirmation = {
  pending_confirmation: true
  message: string
}

export type EmailConfirmed = {
  confirmed: true
  message: string
}

export function isAccount(value: Account | EmailConfirmed): value is Account {
  return typeof (value as Account).id === "number"
}

export type Person = {
  id: number
  display_name: string
  email: string
  role: Role
  member?: boolean
  translation_enabled?: boolean
  paste_enabled?: boolean
}

export type CommunitySummary = {
  id: string
  name: string
  student_count: number
  teacher_count: number
  translation_enabled: boolean
  paste_enabled: boolean
}

export type Community = CommunitySummary & {
  students: Person[]
  teachers: Person[]
}

export type ClassroomStudent = {
  id: number
  display_name: string
  email: string
  communities: string[]
}

export type StudentWork = {
  student: Person
  projects: Array<Project & { algorithms: Algorithm[] }>
}

export type Project = {
  id: string
  name: string
  description: string
  visibility: string
}

export type Algorithm = {
  id: string
  project_id: string
  folder_id: string | null
  name: string
  source: string
  language_profile: string
  require_semicolons: boolean
  index_base: 0 | 1
  current_version: number
  updated_at: string
}

export type Translation = {
  language: string
  label: string
  extension: string
  code: string
}

export type TranslationResult = {
  diagnostics: Diagnostic[]
  translations: Translation[]
}

export type Diagnostic = {
  severity: string
  code: string
  message: string
  line: number
  column: number
  suggestion: string | null
  snippet?: string
}

export type LabBinding = {
  block_id: string
  line: number
  column: number
}

export type LabPreview = {
  source: string
  bindings: LabBinding[]
  diagnostics: Diagnostic[]
}

export type LabPractice = {
  id: string
  name: string
  source: string
  updated_at: string
  workspace?: object
}

export type LabRun = {
  id: string | null
  status: string
  scope?: string
  line: number | null
  column: number | null
  output: string
  variables: Record<string, string>
  pending_input: { name: string; type: string } | null
  diagnostics: Diagnostic[]
  source: string
  bindings: LabBinding[]
  event_cursor: number
}

export type LabPathChallenge = {
  id: string
  title: string
  activity_type: string
  difficulty: number
  points: number
  concept: string
  position: number
  state: "locked" | "available" | "completed" | "scheduled" | "closed"
  opens_at?: string | null
  closes_at?: string | null
  withdrawn?: boolean
  time_limit_seconds: number | null
  attempt_count: number
  score?: number | null
}

export type LabRosterStudent = {
  id: number
  display_name: string
  email: string
  communities: string[]
  completed: number
  total: number
  points: number
  rank: number
  last_activity: string | null
}

export type LabRosterRoute = {
  id: string
  name: string
  description: string
  students: LabRosterStudent[]
}

export type LabRosterPerson = {
  id: number
  display_name: string
  email: string
  role: Role
  points: number
  rank: number
  completed: number
  total: number
  last_activity: string | null
  communities: string[]
  routes: { id: string; name: string }[]
}

export type LabMemberPath = {
  id: string
  name: string
  description: string
  completed: number
  total: number
  challenges: LabPathChallenge[]
}

export type LabMemberProgress = {
  person: LabRosterPerson
  paths: LabMemberPath[]
  mastery: { concept: string; level: number }[]
}

export type LabMemberWork = {
  challenge: LabChallenge
  attempt: {
    status: string
    score: number | null
    summary: string
    elapsed_seconds: number | null
    finished_at: string | null
    reflection: string | null
    prediction: { answer: string; is_correct: boolean } | null
    answer: { label: string; value: string }[]
    source: string
    cases: { name: string; passed: boolean; output: string }[]
  } | null
}

export type LabCatalogChallenge = {
  id: string
  title: string
  activity_type: string
  concept: string
  points: number
  difficulty: number
  position?: number
  owned?: boolean
}

export type LabBankCase = {
  name: string
  inputs: string[]
  expected_output: string
}

export type LabBankChallenge = {
  id: string
  title: string
  prompt: string
  activity_type: string
  concept: string
  difficulty: number
  points: number
  position: number
  time_limit_seconds: number | null
  categories: string[]
  items: { text: string; category: string }[]
  question: string
  accepted: string[]
  inputs: string[]
  expected_output: string
  cases: LabBankCase[]
  source: string
  hints: string[]
  allowed_blocks: string[]
  owned: boolean
}

export type LabBankShelf = {
  name: string
  description: string
  units: { title: string; concept: string; challenges: LabBankChallenge[] }[]
}

export type LabBank = LabBankShelf & {
  contest: LabBankShelf | null
}

export type CsvChallengeFormat = {
  tipo: string
  columns: string[]
  notes: string
  example: string
}

export type LabConcept = {
  key: string
  name: string
}

export type LabChallengeDraft = {
  id: string
  title: string
  prompt: string
  activity_type: string
  concept: string
  difficulty: number
  points: number
  time_limit_seconds: number | null
  owned: boolean
  categories: string[]
  items: { text: string; category: string }[]
  question: string
  accepted: string[]
  inputs: string[]
  expected_output: string
  cases: { name: string; inputs: string[]; expected_output: string }[]
  tools: string[]
  source: string
  hint: string
  hints: string[]
  allowed_blocks: string[]
}

export type LabChallengeInput = {
  title: string
  prompt: string
  activity_type: string
  concept: string
  difficulty: number
  points: number
  time_limit_seconds: number | null
  categories: string[]
  items: { text: string; category: string }[] | string[]
  question: string
  accepted: string[]
  inputs: string[]
  expected_output: string
  cases?: { inputs: string[]; expected_output: string }[]
  tools?: string[]
  source: string
  hints: string[]
  allowed_blocks: string[]
}

export type LabAuthoredChallenge = LabCatalogChallenge & {
  position: number
  opens_at: string | null
  closes_at: string | null
  withdrawn: boolean
}

export type LabAuthoredPath = {
  id: string
  name: string
  description: string
  is_published: boolean
  challenges: LabAuthoredChallenge[]
  communities: { id: string; name: string }[]
  students: { id: number; display_name: string; email: string }[]
}

export type LabAuthoredSummary = {
  id: string
  name: string
  description: string
  is_published: boolean
  challenge_count: number
  community_count: number
  student_count: number
}

export type LabPath = {
  id: string
  name: string
  description: string
  challenges: LabPathChallenge[]
}

export type LabChallenge = {
  id: string
  title: string
  prompt: string
  activity_type: string
  difficulty: number
  points: number
  concept: string
  allowed_blocks: string[]
  time_limit_seconds: number | null
  task: {
    categories?: string[]
    items?: { id: string; text: string }[]
    question?: string
    source?: string
    tools?: string[]
    cases?: { name: string; inputs: string[]; expected_output: string }[]
  }
}

export type LabAttempt = {
  id: string
  status: string
  score: number | null
  summary: string
  next_stage: string
  hints: { level: number; body: string; solution: boolean }[]
  hints_left: number
  solution_next: boolean
  prediction: { answer: string; is_correct: boolean } | null
  reflection: string | null
  time_limit_seconds: number | null
  seconds_left: number | null
  elapsed_seconds: number | null
  finished_at: string | null
}

export type LabAttemptRecord = {
  id: string
  number: number
  status: string
  score: number | null
  elapsed_seconds: number | null
  finished_at: string | null
  summary: string
}

export type LabCase = { name: string; kind: string; passed: boolean; output: string }

export type LabSession = {
  challenge: LabChallenge
  attempt: LabAttempt
  history: LabAttemptRecord[]
  correct?: boolean
  passed?: boolean
  cases?: LabCase[]
  diagnostics?: Diagnostic[]
  output?: string
  source?: string
  points?: number
  rank?: number
}

export type StackFrame = {
  name: string
  line: number | null
}

export type Execution = {
  id: string
  status: string
  output: string
  instruction_count: number
  version_number: number | null
  pending_input: { name: string; type: string } | null
  diagnostics: Diagnostic[]
  debug?: boolean
  line?: number | null
  column?: number | null
  scope?: string
  variables?: Record<string, string>
  call_stack?: StackFrame[]
  last_condition?: string | null
  breakpoints?: number[]
  event_cursor?: number
}

export type FlowNode = {
  id: string
  kind: "terminal" | "process" | "io" | "decision" | "subprocess" | "join"
  figure?: string
  text: string
  line: number | null
  column: number | null
  end_line: number | null
  end_column: number | null
}

export type FlowEdge = {
  source: string
  target: string
  label: string | null
}

export type FlowGraph = {
  entry: string
  nodes: FlowNode[]
  edges: FlowEdge[]
}

export type ArraySlice = {
  name: string
  start: number
  total: number
  lengths: number[]
  base: number
  values: string[]
}

export type Preferences = {
  theme: "light" | "dark"
  font_size: number
  keymap: string
  indent_size: number
  autosave: boolean
  locale: "es" | "en"
  require_semicolons: boolean
  index_base: 0 | 1
}

export type Meta = {
  product: string
  runner: string
  debug: boolean
  notice: string | null
}

export type Page<T> = {
  count: number
  results: T[]
}

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

function readCookie(name: string): string {
  const prefix = `${name}=`
  for (const part of document.cookie.split(";")) {
    const item = part.trim()
    if (item.startsWith(prefix)) return decodeURIComponent(item.slice(prefix.length))
  }
  return ""
}

let memoryCsrf = ""

function csrfToken(): string {
  return memoryCsrf || readCookie("csrftoken")
}

export function attemptCheckPath(attemptId: string): string {
  return `/api/v1/learning/attempts/${attemptId}/check/`
}

function desktopProxyEnabled(): boolean {
  return typeof window !== "undefined" && (window as Window & { __TRAZA_DESKTOP_PROXY__?: boolean }).__TRAZA_DESKTOP_PROXY__ === true
}

async function requestText(path: string): Promise<string> {
  if (desktopProxyEnabled()) {
    const internals = (window as Window & { __TAURI_INTERNALS__?: { invoke: (command: string, args: Record<string, unknown>) => Promise<ProxyReply> } }).__TAURI_INTERNALS__
    if (!internals) throw new ApiError(0, "local_missing", localMissingMessage())
    const reply = await internals.invoke("server_fetch", { path, method: "GET", body: null, headers: {} })
    if (reply.csrf) memoryCsrf = reply.csrf
    if (reply.status < 200 || reply.status >= 300) throw textError(reply.status, reply.body)
    return reply.body
  }
  const response = await fetch(path, { credentials: "same-origin" })
  const text = await response.text()
  if (!response.ok) throw textError(response.status, text)
  return text
}

function textError(status: number, body: string): ApiError {
  try {
    const data = JSON.parse(body) as { error?: { code?: string; message?: string } }
    const error = data.error ?? {}
    return new ApiError(status, error.code ?? "invalid", error.message ?? "No se pudo completar la solicitud.")
  } catch {
    return new ApiError(status, "invalid", "No se pudo completar la solicitud.")
  }
}

let memoryWindow = ""

function browserWindow(): string {
  if (typeof window === "undefined") return ""
  const key = "traza-window"
  try {
    const existing = window.sessionStorage.getItem(key)
    if (existing && /^[A-Za-z0-9-]{8,64}$/.test(existing)) return existing
    const created = window.crypto.randomUUID()
    window.sessionStorage.setItem(key, created)
    return created
  } catch {
    if (!memoryWindow) memoryWindow = window.crypto.randomUUID()
    return memoryWindow
  }
}

function raiseApi(status: number, code: string, message: string): never {
  const ended = status === 401 && (code === "session_idle" || code === "session_open")
  if (ended && typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("traza-session-end", { detail: message }))
  }
  throw new ApiError(status, code, message)
}

function installedClient(): boolean {
  if (typeof window === "undefined") return false
  const host = window as Window & { __TRAZA_LOCAL__?: { origin?: string }; __TAURI_INTERNALS__?: unknown }
  return Boolean(host.__TRAZA_LOCAL__?.origin) || "__TAURI_INTERNALS__" in host
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (desktopProxyEnabled()) return desktopRequest<T>(path, init)
  const headers = new Headers(init.headers)
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json")
  const token = csrfToken()
  if (token) headers.set("X-CSRFToken", token)
  const windowId = browserWindow()
  if (windowId) headers.set("X-Traza-Window", windowId)
  if (installedClient()) headers.set("X-Aulivana-FCDdesign-Client", "desktop")
  const response = await fetch(path, {
    ...init,
    headers,
    credentials: "same-origin",
  })
  if (response.status === 204) return undefined as T
  const raw = await response.text()
  let data: { error?: { code?: string; message?: string } } = {}
  if (raw) {
    try {
      data = JSON.parse(raw) as { error?: { code?: string; message?: string } }
    } catch {
      throw new ApiError(response.status, "invalid", "No se pudo completar la solicitud.")
    }
  }
  if (!response.ok) {
    const error = data.error ?? {}
    raiseApi(
      response.status,
      error.code ?? "invalid",
      error.message ?? "No se pudo completar la solicitud.",
    )
  }
  return data as T
}

type ProxyReply = { status: number; body: string; csrf: string }

async function desktopRequest<T>(path: string, init: RequestInit): Promise<T> {
  const internals = (window as Window & { __TAURI_INTERNALS__?: { invoke: (command: string, args: Record<string, unknown>) => Promise<ProxyReply> } }).__TAURI_INTERNALS__
  if (!internals) throw new ApiError(0, "local_missing", localMissingMessage())
  const headers: Record<string, string> = {}
  if (init.headers) new Headers(init.headers).forEach((value, key) => {
    headers[key] = value
  })
  const token = csrfToken()
  if (token) headers["X-CSRFToken"] = token
  const windowId = browserWindow()
  if (windowId) headers["X-Traza-Window"] = windowId
  if (installedClient()) headers["X-Aulivana-FCDdesign-Client"] = "desktop"
  if (init.body) headers["Content-Type"] = "application/json"
  const reply = await internals.invoke("server_fetch", {
    path,
    method: init.method ?? "GET",
    body: typeof init.body === "string" ? init.body : null,
    headers,
  })
  if (reply.csrf) memoryCsrf = reply.csrf
  if (reply.status === 204) return undefined as T
  const data = JSON.parse(reply.body || "{}") as { error?: { code?: string; message?: string } }
  if (reply.status < 200 || reply.status >= 300) {
    const error = data.error ?? {}
    raiseApi(reply.status, error.code ?? "invalid", error.message ?? "No se pudo completar la solicitud.")
  }
  return data as T
}

export function ensureCsrf(): Promise<{ ok: boolean }> {
  return request("/api/v1/auth/csrf/")
}

export const api = {
  me: () => request<Account>("/api/v1/auth/me/"),
  presence: () =>
    request<Account>("/api/v1/auth/me/", { headers: { "X-Traza-Presence": "1" } }),
  register: (body: { email: string; password: string; display_name?: string; role?: Role }) =>
    request<Account | PendingConfirmation>("/api/v1/auth/register/", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  confirmEmail: (uid: string, token: string) =>
    request<Account | EmailConfirmed>("/api/v1/auth/confirm-email/", {
      method: "POST",
      body: JSON.stringify({ uid, token }),
    }),
  resendConfirmation: (email: string) =>
    request<{ message: string }>("/api/v1/auth/confirm-email/resend/", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  login: (body: { email: string; password: string }) =>
    request<Account>("/api/v1/auth/login/", { method: "POST", body: JSON.stringify(body) }),
  updateAccount: (body: {
    role?: Role
    display_name?: string
    avatar?: string | null
    current_password?: string
    password?: string
  }) => request<Account>("/api/v1/auth/me/", { method: "PATCH", body: JSON.stringify(body) }),
  communities: () => request<{ results: CommunitySummary[] }>("/api/v1/communities/"),
  community: (id: string) => request<Community>(`/api/v1/communities/${id}/`),
  createCommunity: (name: string) =>
    request<Community>("/api/v1/communities/", { method: "POST", body: JSON.stringify({ name }) }),
  deleteCommunity: (id: string) => request<void>(`/api/v1/communities/${id}/`, { method: "DELETE" }),
  addMember: (communityId: string, userId: number) =>
    request<Person>(`/api/v1/communities/${communityId}/members/`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
  removeMember: (communityId: string, userId: number) =>
    request<void>(`/api/v1/communities/${communityId}/members/${userId}/`, { method: "DELETE" }),
  setCommunityTranslation: (id: string, enabled: boolean) =>
    request<Community>(`/api/v1/communities/${id}/`, {
      method: "PATCH",
      body: JSON.stringify({ translation_enabled: enabled }),
    }),
  setMemberTranslation: (communityId: string, userId: number, enabled: boolean) =>
    request<Community>(`/api/v1/communities/${communityId}/members/${userId}/`, {
      method: "PATCH",
      body: JSON.stringify({ translation_enabled: enabled }),
    }),
  setCommunityPaste: (id: string, enabled: boolean) =>
    request<Community>(`/api/v1/communities/${id}/`, {
      method: "PATCH",
      body: JSON.stringify({ paste_enabled: enabled }),
    }),
  setMemberPaste: (communityId: string, userId: number, enabled: boolean) =>
    request<Community>(`/api/v1/communities/${communityId}/members/${userId}/`, {
      method: "PATCH",
      body: JSON.stringify({ paste_enabled: enabled }),
    }),
  searchPeople: (query: string, communityId: string) =>
    request<{ results: Person[] }>(
      `/api/v1/people/?q=${encodeURIComponent(query)}&community=${encodeURIComponent(communityId)}`,
    ),
  classroomStudents: () => request<{ results: ClassroomStudent[] }>("/api/v1/classroom/students/"),
  studentProjects: (userId: number) =>
    request<StudentWork>(`/api/v1/classroom/students/${userId}/projects/`),
  logout: () => request<void>("/api/v1/auth/logout/", { method: "POST" }),
  reset: (email: string) =>
    request<{ message: string }>("/api/v1/auth/password-reset/", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  confirmReset: (uid: string, token: string, password: string) =>
    request<{ message: string }>("/api/v1/auth/password-reset/confirm/", {
      method: "POST",
      body: JSON.stringify({ uid, token, password }),
    }),
  projects: () => request<Page<Project>>("/api/v1/projects/?page_size=100"),
  createProject: (name: string) =>
    request<Project>("/api/v1/projects/", { method: "POST", body: JSON.stringify({ name }) }),
  renameProject: (id: string, name: string) =>
    request<Project>(`/api/v1/projects/${id}/`, { method: "PATCH", body: JSON.stringify({ name }) }),
  algorithms: (projectId: string, page = 1) =>
    request<Page<Algorithm>>(
      `/api/v1/algorithms/?project=${encodeURIComponent(projectId)}&page_size=100&page=${page}`,
    ),
  createAlgorithm: (projectId: string, name: string, source?: string) =>
    request<Algorithm>("/api/v1/algorithms/", {
      method: "POST",
      body: JSON.stringify(source === undefined ? { project_id: projectId, name } : { project_id: projectId, name, source }),
    }),
  renameAlgorithm: (id: string, name: string) =>
    request<Algorithm>(`/api/v1/algorithms/${id}/`, { method: "PATCH", body: JSON.stringify({ name }) }),
  algorithm: (id: string) => request<Algorithm>(`/api/v1/algorithms/${id}/`),
  saveSource: (id: string, source: string, init: RequestInit = {}) =>
    request<Algorithm>(`/api/v1/algorithms/${id}/`, {
      ...init,
      method: "PATCH",
      body: JSON.stringify({ source }),
    }),
  saveLanguageOptions: (id: string, body: { require_semicolons?: boolean; index_base?: 0 | 1 }) =>
    request<Algorithm>(`/api/v1/algorithms/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteAlgorithm: (id: string) => request<void>(`/api/v1/algorithms/${id}/`, { method: "DELETE" }),
  saveVersion: (id: string) =>
    request<{ number: number }>(`/api/v1/algorithms/${id}/save/`, {
      method: "POST",
      body: JSON.stringify({ message: "Guardado" }),
    }),
  validate: (id: string) =>
    request<{ diagnostics: Diagnostic[] }>(`/api/v1/algorithms/${id}/validate/`, { method: "POST" }),
  translate: (id: string) =>
    request<TranslationResult>(`/api/v1/algorithms/${id}/translate/`, { method: "POST" }),
  execute: (id: string) => request<Execution>(`/api/v1/algorithms/${id}/execute/`, { method: "POST" }),
  execution: (id: string) => request<Execution>(`/api/v1/executions/${id}/`),
  debug: (id: string, breakpoints: number[]) =>
    request<Execution>(`/api/v1/algorithms/${id}/debug/`, {
      method: "POST",
      body: JSON.stringify({ breakpoints }),
    }),
  control: (id: string, action: string, breakpoints?: number[]) =>
    request<Execution>(`/api/v1/executions/${id}/control/`, {
      method: "POST",
      body: JSON.stringify(breakpoints ? { action, breakpoints } : { action }),
    }),
  inspect: (id: string, name: string, start = 0, count = 24) =>
    request<ArraySlice>(`/api/v1/executions/${id}/inspect/`, {
      method: "POST",
      body: JSON.stringify({ name, start, count }),
    }),
  sendInput: (id: string, text: string) =>
    request<Execution>(`/api/v1/executions/${id}/input/`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  preferences: () => request<Preferences>("/api/v1/preferences/"),
  updatePreferences: (body: Partial<Preferences>) =>
    request<Preferences>("/api/v1/preferences/", { method: "PATCH", body: JSON.stringify(body) }),
  meta: () => request<Meta>("/api/v1/meta/"),
  keywords: () => request<{ keywords: string[]; stdlib: string[] }>("/api/v1/language/keywords/"),
  flowchart: (id: string) =>
    request<{ graph: FlowGraph | null; diagnostics: Diagnostic[] }>(`/api/v1/algorithms/${id}/flowchart/`),
  practices: () => request<{ results: LabPractice[] }>("/api/v1/learning/practices/"),
  practice: (id: string) => request<LabPractice>(`/api/v1/learning/practices/${id}/`),
  createPractice: (name: string, workspace: object) =>
    request<LabPractice>("/api/v1/learning/practices/", {
      method: "POST",
      body: JSON.stringify({ name, workspace }),
    }),
  updatePractice: (id: string, body: { name?: string; workspace?: object }) =>
    request<LabPractice>(`/api/v1/learning/practices/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deletePractice: (id: string) => request<void>(`/api/v1/learning/practices/${id}/`, { method: "DELETE" }),
  importLab: (source: string) =>
    request<{ workspace: object | null; diagnostics: Diagnostic[] }>("/api/v1/learning/import/", {
      method: "POST",
      body: JSON.stringify({ source }),
    }),
  previewLab: (workspace: object) =>
    request<LabPreview>("/api/v1/learning/preview/", {
      method: "POST",
      body: JSON.stringify({ workspace }),
    }),
  startLab: (workspace: object) =>
    request<LabRun>("/api/v1/learning/run/", {
      method: "POST",
      body: JSON.stringify({ workspace }),
    }),
  labRun: (id: string) => request<LabRun>(`/api/v1/learning/runs/${id}/`),
  controlLab: (id: string, action: string) =>
    request<LabRun>(`/api/v1/learning/runs/${id}/control/`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),
  inputLab: (id: string, text: string) =>
    request<LabRun>(`/api/v1/learning/runs/${id}/input/`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  labPath: () => request<LabPath>("/api/v1/learning/path/"),
  labPaths: () => request<{ results: LabPath[] }>("/api/v1/learning/paths/"),
  labCatalog: () =>
    request<{ results: LabCatalogChallenge[]; concepts: LabConcept[] }>("/api/v1/learning/catalog/"),
  labBank: () => request<LabBank>("/api/v1/learning/bank/"),
  labCsvFormats: () => request<{ types: CsvChallengeFormat[] }>("/api/v1/learning/challenges/csv/"),
  exportLabCsv: (tipo: string, banco: "catalogo" | "concurso") =>
    request<{ tipo: string; filename: string; csv: string; count: number }>(
      `/api/v1/learning/challenges/csv/?tipo=${encodeURIComponent(tipo)}&contenido=retos&banco=${banco}`,
    ),
  importLabCsv: (csv: string) =>
    request<{ created: number; titles: string[] }>("/api/v1/learning/challenges/csv/", {
      method: "POST",
      body: JSON.stringify({ csv }),
    }),
  createLabChallenge: (body: LabChallengeInput) =>
    request<LabChallengeDraft>("/api/v1/learning/authored/challenges/", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  labChallenge: (id: string) => request<LabChallengeDraft>(`/api/v1/learning/authored/challenges/${id}/`),
  updateLabChallenge: (id: string, body: LabChallengeInput) =>
    request<LabChallengeDraft>(`/api/v1/learning/authored/challenges/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteLabChallenge: (id: string) =>
    request<void>(`/api/v1/learning/authored/challenges/${id}/`, { method: "DELETE" }),
  authoredPaths: () => request<{ results: LabAuthoredSummary[] }>("/api/v1/learning/authored/"),
  createLabPath: (name: string, description: string) =>
    request<LabAuthoredPath>("/api/v1/learning/authored/", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  labAuthored: (id: string) => request<LabAuthoredPath>(`/api/v1/learning/authored/${id}/`),
  updateLabPath: (id: string, body: { name?: string; description?: string; is_published?: boolean }) =>
    request<LabAuthoredPath>(`/api/v1/learning/authored/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteLabPath: (id: string) => request<void>(`/api/v1/learning/authored/${id}/`, { method: "DELETE" }),
  setLabChallenges: (id: string, challengeIds: string[]) =>
    request<LabAuthoredPath>(`/api/v1/learning/authored/${id}/challenges/`, {
      method: "PUT",
      body: JSON.stringify({ challenge_ids: challengeIds }),
    }),
  setLabSchedule: (
    pathId: string,
    challengeId: string,
    body: { opens_at?: string | null; closes_at?: string | null; withdrawn?: boolean },
  ) =>
    request<LabAuthoredPath>(`/api/v1/learning/authored/${pathId}/challenges/${challengeId}/`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  setLabAssignments: (id: string, communityIds: string[], studentIds: number[]) =>
    request<LabAuthoredPath>(`/api/v1/learning/authored/${id}/assignments/`, {
      method: "PUT",
      body: JSON.stringify({ community_ids: communityIds, student_ids: studentIds }),
    }),
  labRoster: () => request<{ routes: LabRosterRoute[] }>("/api/v1/learning/roster/"),
  labProgressCsv: (pathId: string, lang: "es" | "en") =>
    requestText(`/api/v1/learning/roster/${pathId}/progress/?lang=${lang}`),
  labMember: (userId: number) => request<LabMemberProgress>(`/api/v1/learning/roster/${userId}/`),
  labMemberWork: (userId: number, challengeId: string) =>
    request<LabMemberWork>(`/api/v1/learning/roster/${userId}/challenges/${challengeId}/`),
  startAttempt: (challengeId: string, pathId?: string) =>
    request<LabSession>(`/api/v1/learning/challenges/${challengeId}/attempts/`, {
      method: "POST",
      body: JSON.stringify(pathId ? { path_id: pathId } : {}),
    }),
  saveStage: (attemptId: string, stage: string, answer: object) =>
    request<LabSession>(`/api/v1/learning/attempts/${attemptId}/stage/`, {
      method: "POST",
      body: JSON.stringify({ stage, answer }),
    }),
  revealHint: (attemptId: string) =>
    request<LabSession>(`/api/v1/learning/attempts/${attemptId}/hint/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  checkAttempt: (attemptId: string, workspace: object) =>
    request<LabSession>(attemptCheckPath(attemptId), {
      method: "POST",
      body: JSON.stringify({ workspace }),
    }),
  runAttempt: (attemptId: string) =>
    request<LabSession>(`/api/v1/learning/attempts/${attemptId}/run/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  expireAttempt: (attemptId: string) =>
    request<LabSession>(`/api/v1/learning/attempts/${attemptId}/expire/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  closeAttempt: (attemptId: string, reflection: string) =>
    request<LabSession>(`/api/v1/learning/attempts/${attemptId}/close/`, {
      method: "POST",
      body: JSON.stringify({ reflection }),
    }),
  planCatalog: () => request<{ results: PlanFeature[] }>("/api/v1/billing/catalog/"),
  plans: () => request<{ results: BillingPlan[] }>("/api/v1/billing/plans/"),
  createPlan: (body: BillingPlanInput) =>
    request<BillingPlan>("/api/v1/billing/plans/", { method: "POST", body: JSON.stringify(body) }),
  updatePlan: (id: string, body: Partial<BillingPlanInput>) =>
    request<BillingPlan>(`/api/v1/billing/plans/${id}/`, { method: "PATCH", body: JSON.stringify(body) }),
  subscribers: (query: string, page = 1) =>
    request<{ results: Subscriber[]; count: number; page: number; pages: number }>(
      `/api/v1/billing/users/?q=${encodeURIComponent(query)}&page=${page}`,
    ),
  assignPlan: (
    userId: number,
    body: { plan_id?: string; paid_until?: string | null; browser_allowed?: boolean | null },
  ) =>
    request<Subscriber>(`/api/v1/billing/users/${userId}/`, { method: "PATCH", body: JSON.stringify(body) }),
}
