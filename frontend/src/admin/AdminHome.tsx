import { useEffect, useState } from "react"

import { ApiError, api, type Account, type BillingPlan, type PlanFeature, type Role, type Subscriber } from "../api"
import { useT } from "../i18n"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"

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
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  async function load() {
    const [features, listed] = await Promise.all([api.planCatalog(), api.plans()])
    setCatalog(features.results)
    setPlans(listed.results)
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
    const body = {
      name: draft.name.trim(),
      price_cents: price,
      currency: draft.currency.trim(),
      period_days: period,
      browser_allowed: draft.browser_allowed,
      max_projects: draft.max_projects === "" ? null : Number(draft.max_projects),
      max_algorithms: draft.max_algorithms === "" ? null : Number(draft.max_algorithms),
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

  const visible = catalog.filter((item) => (draft ? item.audiences.includes(draft.audience) : false))

  return (
    <div className="shell">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1><Logo mark />{t("levels")}</h1>
          <AccountIdentity account={account} onAccount={onAccount} />
        </div>
        <div className="actions">
          <button className="top-leave" type="button" onClick={onLogout}>
            {t("leave")}
          </button>
        </div>
      </header>
      <main className="admin-home">
        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="note">{notice}</p> : null}
        <section>
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
                          <span>{plan.browser_allowed ? t("browserOn") : t("browserOff")}</span>
                        </button>
                      </li>
                    ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
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
            </div>
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
            <fieldset className="feature-grid">
              <legend>{t("features")}</legend>
              {visible.map((item) => (
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
            </fieldset>
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
        <section>
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
                </tr>
              </thead>
              <tbody>
                {people.length === 0 ? (
                  <tr>
                    <td colSpan={5}>{t("noAccounts")}</td>
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
      </main>
    </div>
  )
}

function money(cents: number, currency: string): string {
  return `${(cents / 100).toFixed(2)} ${currency}`
}
