import { useEffect, useState } from "react"

import { ApiError, api, type Account, type BillingPlan, type PlanFeature, type Role, type SignupPolicy, type Subscriber } from "../api"
import { useT } from "../i18n"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { AdminSessions } from "./AdminSessions"

type Draft = {
  id: string | null
  code: string
  name: string
  audience: Role
  price: string
  currency: string
  period_days: string
  browser_allowed: boolean
  max_projects: string
  max_algorithms: string
  max_executions: string
  features: Record<string, boolean>
  is_active: boolean
  is_default: boolean
}

export function AdminHome({
  account,
  onAccount,
  onLogout,
}: {
  account: Account
  onAccount: (account: Account) => void
  onLogout: () => void
}) {
  const t = useT()
  const [catalog, setCatalog] = useState<PlanFeature[]>([])
  const [plans, setPlans] = useState<BillingPlan[]>([])
  const [draft, setDraft] = useState<Draft | null>(null)
  const [query, setQuery] = useState("")
  const [appliedQuery, setAppliedQuery] = useState("")
  const [people, setPeople] = useState<Subscriber[]>([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [count, setCount] = useState(0)
  const [signup, setSignup] = useState<SignupPolicy | null>(null)
  const [lifetimeHours, setLifetimeHours] = useState("")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [panel, setPanel] = useState<"levels" | "live">("levels")
  const [section, setSection] = useState<"plans" | "accounts" | "access">("plans")
  const [featureSubject, setFeatureSubject] = useState<
    "fundamentos" | "bases" | "objetos" | "software" | "shared"
  >("fundamentos")

  async function load() {
    const [features, listed, gates, lifetime] = await Promise.all([
      api.planCatalog(),
      api.plans(),
      api.signup(),
      api.messageLifetime(),
    ])
    setCatalog(features.results)
    setPlans(listed.results)
    setSignup(gates)
    setLifetimeHours(String(lifetime.hours))
  }

  async function loadPeople(nextPage: number, nextQuery = query) {
    const listed = await api.subscribers(nextQuery, nextPage)
    setPeople(listed.results)
    setPage(listed.page)
    setPages(listed.pages)
    setCount(listed.count)
  }

  useEffect(() => {
    void Promise.all([load(), loadPeople(1, "")]).catch((caught: unknown) => {
      setError(caught instanceof ApiError ? caught.message : t("requestError"))
    })
  }, [])

  function blank(audience: Role): Draft {
    const features: Record<string, boolean> = {}
    for (const item of catalog) {
      if (item.audiences.includes(audience)) features[item.key] = false
    }
    return {
      id: null,
      code: "",
      name: "",
      audience,
      price: "0",
      currency: "MXN",
      period_days: "30",
      browser_allowed: false,
      max_projects: "",
      max_algorithms: "",
      max_executions: "3",
      features,
      is_active: true,
      is_default: false,
    }
  }

  function open(plan: BillingPlan) {
    setError("")
    setNotice("")
    setDraft({
      id: plan.id,
      code: plan.code,
      name: plan.name,
      audience: plan.audience,
      price: (plan.price_cents / 100).toFixed(2),
      currency: plan.currency,
      period_days: String(plan.period_days),
      browser_allowed: plan.browser_allowed,
      max_projects: plan.max_projects === null ? "" : String(plan.max_projects),
      max_algorithms: plan.max_algorithms === null ? "" : String(plan.max_algorithms),
      max_executions: plan.max_executions_per_day === null ? "" : String(plan.max_executions_per_day),
      features: { ...plan.features },
      is_active: plan.is_active,
      is_default: plan.is_default,
    })
  }

  async function save() {
    if (!draft) return
    setError("")
    setNotice("")
    const price = Math.round(Number(draft.price) * 100)
    const period = Number(draft.period_days)
    if (!Number.isFinite(price) || price < 0 || !Number.isInteger(period) || period < 0) {
      setError(t("planInvalid"))
      return
    }
    const executions = draft.max_executions === "" ? null : Number(draft.max_executions)
    if (executions !== null && (!Number.isInteger(executions) || executions < 3)) {
      setError(t("planExecutionsInvalid"))
      return
    }
    const body = {
      name: draft.name.trim(),
      price_cents: price,
      currency: draft.currency.trim(),
      period_days: period,
      browser_allowed: draft.browser_allowed,
      max_projects: draft.max_projects === "" ? null : Number(draft.max_projects),
      max_algorithms: draft.max_algorithms === "" ? null : Number(draft.max_algorithms),
      max_executions_per_day: executions,
      features: draft.features,
      is_active: draft.is_active,
    }
    try {
      if (draft.id) {
        await api.updatePlan(draft.id, body)
      } else {
        await api.createPlan({ ...body, code: draft.code.trim(), audience: draft.audience })
      }
      setNotice(t("planSaved"))
      setDraft(null)
      await load()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("requestError"))
    }
  }

  async function search(nextPage = 1, nextQuery = query) {
    setError("")
    setAppliedQuery(nextQuery)
    try {
      await loadPeople(nextPage, nextQuery)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("requestError"))
    }
  }

  async function assign(person: Subscriber, planId: string) {
    setError("")
    try {
      const saved = await api.assignPlan(person.id, { plan_id: planId })
      setPeople((rows) => rows.map((row) => (row.id === saved.id ? saved : row)))
      setNotice(t("planAssigned"))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("requestError"))
    }
  }

  async function setSignupFlag(key: keyof SignupPolicy, value: boolean) {
    setSignup((current) => (current ? { ...current, [key]: value } : current))
    setError("")
    try {
      const saved = await api.updateSignup({ [key]: value })
      setSignup(saved)
      setNotice(t("signupSaved"))
    } catch (caught) {
      setSignup(await api.signup().catch(() => null))
      setError(caught instanceof ApiError ? caught.message : t("requestError"))
    }
  }

  async function saveLifetime(event: { preventDefault: () => void }) {
    event.preventDefault()
    const hours = Number(lifetimeHours)
    if (!Number.isInteger(hours) || hours < 1 || hours > 8760) {
      setError(t("chatLifetimeInvalid"))
      setNotice("")
      return
    }
    setError("")
    try {
      const saved = await api.updateMessageLifetime({ hours })
      setLifetimeHours(String(saved.hours))
      setNotice(t("chatLifetimeSaved"))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("requestError"))
    }
  }

  async function setBlocked(person: Subscriber, blocked: boolean) {
    if (blocked && !window.confirm(t("blockConfirm", { name: person.display_name }))) return
    setError("")
    try {
      const saved = await api.assignPlan(person.id, { blocked })
      setPeople((rows) => rows.map((row) => (row.id === saved.id ? saved : row)))
      setNotice(blocked ? t("accountBlockedSaved") : t("accountUnblockedSaved"))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("requestError"))
    }
  }

  async function allowBrowser(person: Subscriber, allowed: boolean) {
    setError("")
    try {
      const saved = await api.assignPlan(person.id, { browser_allowed: allowed ? true : null })
      setPeople((rows) => rows.map((row) => (row.id === saved.id ? saved : row)))
      setNotice(t("planAssigned"))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("requestError"))
    }
  }

  const featureSubjects = ["fundamentos", "bases", "objetos", "software", "shared"] as const
  const subjectFlag: Record<string, string> = {
    fundamentos: "subject_fundamentos",
    bases: "subject_bases",
    objetos: "subject_objetos",
    software: "subject_software",
  }
  const visible = catalog.filter((item) => (draft ? item.audiences.includes(draft.audience) : false))
  const inSubject = visible.filter((item) => item.subject === featureSubject && item.group !== "subjects")
  const grouped = (["menus", "editor", "lab", "classroom"] as const)
    .map((group) => ({ group, items: inSubject.filter((item) => item.group === group) }))
    .filter((entry) => entry.items.length > 0)

  function subjectTitle(subject: string) {
    if (subject === "bases") return t("subjectBases")
    if (subject === "objetos") return t("subjectObjects")
    if (subject === "software") return t("subjectSoftware")
    if (subject === "shared") return t("featureShared")
    return t("subjectFundamentos")
  }

  function groupName(group: string) {
    if (group === "menus") return t("featureGroupMenus")
    if (group === "classroom") return t("featureGroupClassroom")
    if (group === "lab") return t("featureGroupLab")
    return t("featureGroupEditor")
  }

  function tally(subject: string) {
    const items = visible.filter((item) => item.subject === subject)
    return {
      on: items.filter((item) => draft?.features[item.key] === true).length,
      total: items.length,
    }
  }

  function setGroup(keys: string[], on: boolean) {
    setDraft((current) => {
      if (!current) return current
      const features = { ...current.features }
      for (const key of keys) features[key] = on
      return { ...current, features }
    })
  }

  return (
    <div className="shell">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1><Logo mark />{panel === "live" ? t("connected") : t("levels")}</h1>
          <AccountIdentity account={account} onAccount={onAccount} />
        </div>
        <div className="actions">
          <button
            className="top-action"
            type="button"
            aria-current={panel === "levels" ? "page" : undefined}
            onClick={() => setPanel("levels")}
          >
            {t("levels")}
          </button>
          <button
            className="top-action"
            type="button"
            aria-current={panel === "live" ? "page" : undefined}
            onClick={() => setPanel("live")}
          >
            {t("connected")}
          </button>
          <button className="top-leave" type="button" onClick={onLogout}>
            {t("leave")}
          </button>
        </div>
      </header>
      <main className="admin-home">
        {panel === "live" ? <AdminSessions selfId={account.id} /> : null}
        {panel === "levels" && error ? <p className="error">{error}</p> : null}
        {panel === "levels" && notice ? <p className="note">{notice}</p> : null}
        {panel === "levels" ? (<>
        <nav className="admin-sections" aria-label={t("levels")}>
          <button type="button" aria-current={section === "plans" ? "page" : undefined} onClick={() => setSection("plans")}>
            {t("levels")}
          </button>
          <button type="button" aria-current={section === "accounts" ? "page" : undefined} onClick={() => setSection("accounts")}>
            {t("accounts")}
          </button>
          <button type="button" aria-current={section === "access" ? "page" : undefined} onClick={() => setSection("access")}>
            {t("adminAccess")}
          </button>
        </nav>
        {section === "access" ? (<>
        <section className="admin-block">
          <h2>{t("signupTitle")}</h2>
          <p className="note">{t("signupHint")}</p>
          {signup ? (
            <div className="signup-gates">
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={signup.student}
                  onChange={(event) => void setSignupFlag("student", event.target.checked)}
                />
                {t("signupStudent")}
              </label>
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={signup.teacher}
                  onChange={(event) => void setSignupFlag("teacher", event.target.checked)}
                />
                {t("signupTeacher")}
              </label>
            </div>
          ) : null}
        </section>
        <section className="admin-block">
          <h2>{t("chatLifetimeTitle")}</h2>
          <p className="note">{t("chatLifetimeHint")}</p>
          <form className="admin-search" onSubmit={(event) => void saveLifetime(event)}>
            <label>
              {t("chatLifetimeHours")}
              <input
                value={lifetimeHours}
                inputMode="numeric"
                onChange={(event) => setLifetimeHours(event.target.value)}
                required
              />
            </label>
            <button className="primary" type="submit">
              {t("save")}
            </button>
          </form>
        </section>
        </>) : null}
        {section === "plans" ? (<>
        <section className="admin-block">
          <header className="admin-head">
            <h2>{t("levels")}</h2>
            <div>
              <button type="button" onClick={() => setDraft(blank("student"))}>
                {t("newStudentPlan")}
              </button>
              <button type="button" onClick={() => setDraft(blank("teacher"))}>
                {t("newTeacherPlan")}
              </button>
            </div>
          </header>
          <p className="note">{t("levelsHint")}</p>
          <div className={draft ? "plan-studio" : undefined}>
          <div className="plan-groups">
            {(["student", "teacher"] as const).map((audience) => (
              <div key={audience}>
                <h3>{audience === "teacher" ? t("teacher") : t("student")}</h3>
                <ul className="plan-list">
                  {plans
                    .filter((plan) => plan.audience === audience)
                    .map((plan) => (
                      <li key={plan.id}>
                        <button
                          type="button"
                          aria-pressed={draft?.id === plan.id}
                          onClick={() => open(plan)}
                        >
                          <strong>{plan.name}</strong>
                          <span>{money(plan.price_cents, plan.currency)}</span>
                          <span>
                            {t("featureOnCount", {
                              on: Object.values(plan.features).filter(Boolean).length,
                              total: Object.keys(plan.features).length,
                            })}
                          </span>
                          <span>{plan.browser_allowed ? t("browserOn") : t("browserOff")}</span>
                        </button>
                      </li>
                    ))}
                </ul>
              </div>
            ))}
          </div>
        {draft ? (
          <form
            className="card account-card"
            onSubmit={(event) => {
              event.preventDefault()
              void save()
            }}
          >
            <h2>{draft.id ? draft.name : t("newPlan")}</h2>
            <div className="admin-fields">
              {draft.id ? null : (
                <label>
                  {t("planCode")}
                  <input value={draft.code} required onChange={(event) => setDraft({ ...draft, code: event.target.value })} />
                </label>
              )}
              <label>
                {t("nameWord")}
                <input value={draft.name} required onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
              </label>
              <label>
                {t("price")}
                <input value={draft.price} inputMode="decimal" onChange={(event) => setDraft({ ...draft, price: event.target.value })} />
              </label>
              <label>
                {t("currency")}
                <input value={draft.currency} maxLength={3} onChange={(event) => setDraft({ ...draft, currency: event.target.value })} />
              </label>
              <label>
                {t("periodDays")}
                <input value={draft.period_days} inputMode="numeric" onChange={(event) => setDraft({ ...draft, period_days: event.target.value })} />
              </label>
              <label>
                {t("maxProjects")}
                <input
                  value={draft.max_projects}
                  placeholder={t("unlimited")}
                  onChange={(event) => setDraft({ ...draft, max_projects: event.target.value })}
                />
              </label>
              <label>
                {t("maxAlgorithms")}
                <input
                  value={draft.max_algorithms}
                  placeholder={t("unlimited")}
                  onChange={(event) => setDraft({ ...draft, max_algorithms: event.target.value })}
                />
              </label>
              <label>
                {t("maxExecutions")}
                <input
                  value={draft.max_executions}
                  placeholder={t("unlimited")}
                  onChange={(event) => setDraft({ ...draft, max_executions: event.target.value })}
                />
                <span className="note">{t("maxExecutionsHint")}</span>
              </label>
            </div>
            <div className="admin-switches">
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={draft.browser_allowed}
                  onChange={(event) => setDraft({ ...draft, browser_allowed: event.target.checked })}
                />
                {t("browserAccess")}
              </label>
              {draft.is_default ? null : (
                <label className="check-row">
                  <input
                    type="checkbox"
                    checked={draft.is_active}
                    onChange={(event) => setDraft({ ...draft, is_active: event.target.checked })}
                  />
                  {t("planActive")}
                </label>
              )}
            </div>
            <div className="feature-groups">
              <h3>{t("features")}</h3>
              <p className="note">{t("featureSubjectHint")}</p>
              <div className="feature-subjects" role="tablist" aria-label={t("features")}>
                {featureSubjects.map((subject) => {
                  const count = tally(subject)
                  return (
                    <button
                      key={subject}
                      type="button"
                      role="tab"
                      aria-selected={featureSubject === subject}
                      aria-pressed={featureSubject === subject}
                      onClick={() => setFeatureSubject(subject)}
                    >
                      {subjectTitle(subject)}
                      <small>{t("featureOnCount", count)}</small>
                    </button>
                  )
                })}
              </div>
              {subjectFlag[featureSubject] ? (
                <label className="check-row">
                  <input
                    type="checkbox"
                    checked={draft.features[subjectFlag[featureSubject]] === true}
                    onChange={(event) =>
                      setDraft({
                        ...draft,
                        features: { ...draft.features, [subjectFlag[featureSubject]]: event.target.checked },
                      })
                    }
                  />
                  {t("featureSubjectEnter")}
                </label>
              ) : (
                <p className="note">{t("featureSharedHint")}</p>
              )}
              {featureSubject === "bases" ? <p className="note">{t("featureBasesNote")}</p> : null}
              {featureSubject === "objetos" || featureSubject === "software" ? (
                <p className="note">{t("featureClosedSubject")}</p>
              ) : null}
              {grouped.map((entry) => {
                const keys = entry.items.map((item) => item.key)
                const on = keys.filter((key) => draft.features[key] === true).length
                return (
                  <section className="feature-group" key={entry.group}>
                    <header>
                      <div>
                        <h3>{groupName(entry.group)}</h3>
                        <p className="note">{t("featureOnCount", { on, total: keys.length })}</p>
                      </div>
                      <div className="feature-picks">
                        <button type="button" onClick={() => setGroup(keys, true)}>{t("featureAll")}</button>
                        <button type="button" onClick={() => setGroup(keys, false)}>{t("featureNone")}</button>
                      </div>
                    </header>
                    <div className="feature-grid">
                      {entry.items.map((item) => (
                        <label key={item.key} className="check-row">
                          <input
                            type="checkbox"
                            checked={draft.features[item.key] === true}
                            onChange={(event) =>
                              setDraft({ ...draft, features: { ...draft.features, [item.key]: event.target.checked } })
                            }
                          />
                          {item.label}
                        </label>
                      ))}
                    </div>
                  </section>
                )
              })}
            </div>
            <div className="profile-actions">
              <button type="button" onClick={() => setDraft(null)}>
                {t("cancel")}
              </button>
              <button className="primary" type="submit">
                {t("save")}
              </button>
            </div>
          </form>
        ) : null}
          </div>
        </section>
        </>) : null}
        {section === "accounts" ? (
        <section className="admin-block">
          <header className="admin-head">
            <div>
              <h2>{t("accounts")}</h2>
              <p className="note">{count === 1 ? t("accountsCountOne") : t("accountsCount", { count })}</p>
            </div>
            <form
              className="admin-search"
              onSubmit={(event) => {
                event.preventDefault()
                void search(1)
              }}
            >
              <label>
                {t("searchAccount")}
                <input value={query} onChange={(event) => setQuery(event.target.value)} />
              </label>
              <button type="submit">{t("search")}</button>
            </form>
          </header>
          <div className="table-scroll">
            <table className="account-table">
              <thead>
                <tr>
                  <th>{t("nameWord")}</th>
                  <th>{t("email")}</th>
                  <th>{t("accountType")}</th>
                  <th>{t("planWord")}</th>
                  <th>{t("browserOn")}</th>
                  <th>{t("accountState")}</th>
                </tr>
              </thead>
              <tbody>
                {people.length === 0 ? (
                  <tr>
                    <td colSpan={6}>{t("noAccounts")}</td>
                  </tr>
                ) : (
                  people.map((person) => {
                    const choices = plans.filter(
                      (plan) => plan.audience === person.role && (plan.is_active || plan.code === person.plan?.code),
                    )
                    const selected = choices.find((plan) => plan.code === person.plan?.code)?.id ?? ""
                    return (
                      <tr key={person.id}>
                        <td>{person.display_name}</td>
                        <td>{person.email}</td>
                        <td>{person.role === "teacher" ? t("teacher") : t("student")}</td>
                        <td>
                          <select
                            aria-label={t("planWord")}
                            value={selected}
                            onChange={(event) => {
                              if (event.target.value) void assign(person, event.target.value)
                            }}
                          >
                            {selected ? null : <option value="">{person.plan?.name ?? t("planWord")}</option>}
                            {choices.map((plan) => (
                              <option key={plan.id} value={plan.id}>
                                {plan.name}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <label className="check-row">
                            <input
                              type="checkbox"
                              aria-label={t("accountBrowser")}
                              checked={person.browser_allowed === true}
                              onChange={(event) => void allowBrowser(person, event.target.checked)}
                            />
                          </label>
                        </td>
                        <td>
                          <button
                            type="button"
                            className={person.blocked ? "primary" : undefined}
                            onClick={() => void setBlocked(person, !person.blocked)}
                          >
                            {person.blocked ? t("unblockAccount") : t("blockAccount")}
                          </button>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
          <div className="admin-pager">
            <button type="button" disabled={page <= 1} onClick={() => void search(page - 1, appliedQuery)}>
              {t("previousPage")}
            </button>
            <span>{t("pageStatus", { page, pages })}</span>
            <button type="button" disabled={page >= pages} onClick={() => void search(page + 1, appliedQuery)}>
              {t("nextPage")}
            </button>
          </div>
        </section>
        ) : null}
        </>) : null}
      </main>
    </div>
  )
}

function money(cents: number, currency: string): string {
  return `${(cents / 100).toFixed(2)} ${currency}`
}
