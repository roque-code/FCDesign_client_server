import { useEffect, useState, type FormEvent } from "react"

import { api, ApiError, type Account, type Community, type CommunitySummary, type Person } from "../api"
import { translatedMessage, useT } from "../i18n"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { LeaveSubjectButton } from "../subjects/leave"

const PAGE = 15

function matches(person: Person, text: string): boolean {
  const needle = text.trim().toLocaleLowerCase()
  if (needle === "") return true
  return (
    person.display_name.toLocaleLowerCase().includes(needle) ||
    person.email.toLocaleLowerCase().includes(needle)
  )
}

export function CommunitiesPanel({
  account,
  onAccount,
  onBack,
  backTo = "editor",
}: {
  account: Account
  onAccount: (account: Account) => void
  onBack: () => void
  backTo?: "editor" | "subjects"
}) {
  const t = useT()
  const [communities, setCommunities] = useState<CommunitySummary[]>([])
  const [selectedId, setSelectedId] = useState("")
  const [detail, setDetail] = useState<Community | null>(null)
  const [name, setName] = useState("")
  const [memberQuery, setMemberQuery] = useState("")
  const [page, setPage] = useState(0)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState("")

  async function loadList(prefer?: string) {
    const page = await api.communities()
    setCommunities(page.results)
    const next = prefer && page.results.some((item) => item.id === prefer)
      ? prefer
      : page.results[0]?.id ?? ""
    setSelectedId(next)
    if (!next) setDetail(null)
  }

  useEffect(() => {
    void loadList().catch((caught: unknown) => {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("communitiesLoadError"))
    })
  }, [])

  useEffect(() => {
    setMemberQuery("")
    setPage(0)
  }, [selectedId])

  useEffect(() => {
    if (!selectedId) return
    let alive = true
    void api.community(selectedId).then((item) => {
      if (alive) setDetail(item)
    }).catch((caught: unknown) => {
      if (alive) setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("communityOpenError"))
    })
    return () => {
      alive = false
    }
  }, [selectedId])

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onBack()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onBack])

  async function create(event: FormEvent) {
    event.preventDefault()
    setError("")
    try {
      const created = await api.createCommunity(name.trim())
      setName("")
      setDetail(created)
      await loadList(created.id)
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("communityCreateError"))
    }
  }

  async function removeCommunity() {
    if (!detail) return
    if (!window.confirm(t("deleteCommunity", { name: detail.name }))) return
    setError("")
    try {
      await api.deleteCommunity(detail.id)
      await loadList()
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("communityDeleteError"))
    }
  }

  async function copyCode() {
    if (!detail) return
    try {
      await navigator.clipboard.writeText(detail.join_code)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  async function renewCode() {
    if (!detail) return
    if (!window.confirm(t("newJoinCodeConfirm"))) return
    setError("")
    setCopied(false)
    try {
      remember(await api.renewJoinCode(detail.id))
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("renewCodeError"))
    }
  }

  async function remove(person: Person) {
    if (!selectedId) return
    setError("")
    try {
      await api.removeMember(selectedId, person.id)
      setDetail(await api.community(selectedId))
      setCommunities((await api.communities()).results)
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("removeError"))
    }
  }

  function remember(saved: Community) {
    setDetail(saved)
    setCommunities((rows) =>
      rows.map((item) =>
        item.id === saved.id
          ? { ...item, translation_enabled: saved.translation_enabled, paste_enabled: saved.paste_enabled }
          : item,
      ),
    )
  }

  async function setGroupTranslation(enabled: boolean) {
    if (!selectedId) return
    setError("")
    try {
      remember(await api.setCommunityTranslation(selectedId, enabled))
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("translationSaveError"))
    }
  }

  async function setGroupPaste(enabled: boolean) {
    if (!selectedId) return
    setError("")
    try {
      remember(await api.setCommunityPaste(selectedId, enabled))
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("pasteSaveError"))
    }
  }

  async function setStudentPaste(person: Person, enabled: boolean) {
    if (!selectedId) return
    setError("")
    try {
      remember(await api.setMemberPaste(selectedId, person.id, enabled))
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("pasteSaveError"))
    }
  }

  async function setStudentTranslation(person: Person, enabled: boolean) {
    if (!selectedId) return
    setError("")
    try {
      remember(await api.setMemberTranslation(selectedId, person.id, enabled))
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("translationSaveError"))
    }
  }

  const listed = detail?.students.filter((person) => matches(person, memberQuery)) ?? []
  const pages = Math.max(1, Math.ceil(listed.length / PAGE))
  const safePage = Math.min(page, pages - 1)
  const visibleStudents = listed.slice(safePage * PAGE, safePage * PAGE + PAGE)
  const rangeFrom = listed.length === 0 ? 0 : safePage * PAGE + 1
  const rangeTo = Math.min(listed.length, safePage * PAGE + PAGE)

  return (
    <div className="shell communities-screen">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1><Logo mark />{t("communities")}</h1>
          <AccountIdentity account={account} onAccount={onAccount} />
        </div>
        <div className="actions">
          <LeaveSubjectButton />
          <button className="top-leave" type="button" onClick={onBack}>
            {t(backTo === "subjects" ? "backToSubjects" : "backToEditor")}
          </button>
        </div>
      </header>
      <div className="communities-body">
          <div className="communities-list">
            <form onSubmit={create}>
              <label>
                {t("newCommunity")}
                <input
                  aria-label={t("communityName")}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  required
                />
              </label>
              <button className="primary" type="submit">{t("create")}</button>
            </form>
            <ul>
              {communities.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    aria-current={item.id === selectedId}
                    onClick={() => {
                      setSelectedId(item.id)
                      setCopied(false)
                    }}
                  >
                    <strong>{item.name}</strong>
                    <span>{t(item.student_count === 1 ? "countStudent" : "countStudents", { count: item.student_count })}</span>
                  </button>
                </li>
              ))}
            </ul>
            {communities.length === 0 && <p className="note">{t("communityEmpty")}</p>}
          </div>
          <div className="communities-detail">
            {detail ? (
              <>
                <div className="community-head">
                  <div className="communities-title">
                    <h3>{detail.name}</h3>
                    <button type="button" className="danger" onClick={() => void removeCommunity()}>{t("remove")}</button>
                  </div>
                  <div className="community-switches">
                    <label className="translation-switch">
                      <input
                        type="checkbox"
                        role="switch"
                        checked={detail.translation_enabled}
                        onChange={(event) => void setGroupTranslation(event.target.checked)}
                      />
                      <span>{t("translationForGroup")}</span>
                    </label>
                    <label className="translation-switch">
                      <input
                        type="checkbox"
                        role="switch"
                        checked={!detail.paste_enabled}
                        onChange={(event) => void setGroupPaste(!event.target.checked)}
                      />
                      <span>{t("blockPasteForGroup")}</span>
                    </label>
                  </div>
                  {error && <p className="error">{error}</p>}
                </div>
                <section className="community-code">
                  <h4>{t("joinCode")}</h4>
                  <p className="note">{t("joinCodeNote")}</p>
                  <div className="community-code-row">
                    <strong className="join-code">{detail.join_code}</strong>
                    <button type="button" onClick={() => void copyCode()}>{copied ? t("copied") : t("copy")}</button>
                    <button type="button" onClick={() => void renewCode()}>{t("newJoinCode")}</button>
                  </div>
                </section>
                <section className="community-roster">
                  <div className="roster-tools">
                    <h4>{t("students")}</h4>
                    <input
                      aria-label={t("filterMembers")}
                      value={memberQuery}
                      placeholder={t("filterMembersPlaceholder")}
                      onChange={(event) => {
                        setMemberQuery(event.target.value)
                        setPage(0)
                      }}
                    />
                  </div>
                  <div className="member-scroll">
                    {detail.students.length === 0 ? <p className="note">{t("noStudents")}</p> : null}
                    {detail.students.length > 0 && listed.length === 0 ? <p className="note">{t("noMemberMatch")}</p> : null}
                    <MemberList
                      people={visibleStudents}
                      empty=""
                      removeLabel={t("removeMember")}
                      onRemove={remove}
                      onTranslation={(person, enabled) => void setStudentTranslation(person, enabled)}
                      onPaste={(person, enabled) => void setStudentPaste(person, enabled)}
                    />
                  </div>
                  {pages > 1 ? (
                    <div className="member-pager">
                      <button type="button" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>
                        {t("previousPage")}
                      </button>
                      <span>{t("memberRange", { from: rangeFrom, to: rangeTo, total: listed.length })}</span>
                      <button type="button" disabled={safePage >= pages - 1} onClick={() => setPage(safePage + 1)}>
                        {t("nextPage")}
                      </button>
                    </div>
                  ) : null}
                </section>
                <section className="community-teachers">
                  <h4>{t("teachers")}</h4>
                  <MemberList people={detail.teachers} empty={t("noTeachers")} removeLabel={t("removeMember")} onRemove={remove} />
                </section>
              </>
            ) : (
              <>
                <p className="note">{t("pickCommunity")}</p>
                {error && <p className="error">{error}</p>}
              </>
            )}
          </div>
        </div>
    </div>
  )
}

function MemberList({
  people,
  empty,
  removeLabel,
  onRemove,
  onTranslation,
  onPaste,
}: {
  people: Person[]
  empty: string
  removeLabel: string
  onRemove: (person: Person) => void
  onTranslation?: (person: Person, enabled: boolean) => void
  onPaste?: (person: Person, enabled: boolean) => void
}) {
  const t = useT()
  if (people.length === 0) return empty ? <p className="note">{empty}</p> : null
  return (
    <ul className="member-list">
      {people.map((person) => (
        <li key={person.id}>
          <span>
            <strong>{person.display_name}</strong>
            <small>{person.email}</small>
          </span>
          <span className="member-actions">
            {onTranslation && (
              <label className="translation-switch">
                <input
                  type="checkbox"
                  role="switch"
                  checked={person.translation_enabled !== false}
                  aria-label={t("translationForStudent", { name: person.display_name })}
                  onChange={(event) => onTranslation(person, event.target.checked)}
                />
                <span>{t("translationShort")}</span>
              </label>
            )}
            {onPaste && (
              <label className="translation-switch">
                <input
                  type="checkbox"
                  role="switch"
                  checked={person.paste_enabled === false}
                  aria-label={t("blockPasteForStudent", { name: person.display_name })}
                  onChange={(event) => onPaste(person, !event.target.checked)}
                />
                <span>{t("blockPasteShort")}</span>
              </label>
            )}
            <button type="button" className="danger" onClick={() => onRemove(person)}>{removeLabel}</button>
          </span>
        </li>
      ))}
    </ul>
  )
}
