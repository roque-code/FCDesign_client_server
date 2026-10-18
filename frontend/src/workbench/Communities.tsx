import { useEffect, useState, type FormEvent } from "react"

import { api, ApiError, type Community, type CommunitySummary, type Person } from "../api"
import { translatedMessage, useT } from "../i18n"

export function CommunitiesPanel({ onClose }: { onClose: () => void }) {
  const t = useT()
  const [communities, setCommunities] = useState<CommunitySummary[]>([])
  const [selectedId, setSelectedId] = useState("")
  const [detail, setDetail] = useState<Community | null>(null)
  const [name, setName] = useState("")
  const [query, setQuery] = useState("")
  const [people, setPeople] = useState<Person[]>([])
  const [searched, setSearched] = useState("")
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
      if (event.key === "Escape") onClose()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  useEffect(() => {
    const text = query.trim()
    if (!selectedId || text.length < 2) {
      setPeople([])
      setSearched("")
      return
    }
    const handle = window.setTimeout(() => {
      void api.searchPeople(text, selectedId).then((page) => {
        setPeople(page.results)
        setSearched(text)
      }).catch((caught: unknown) => {
        setPeople([])
        setSearched(text)
        setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("searchError"))
      })
    }, 250)
    return () => window.clearTimeout(handle)
  }, [query, selectedId])

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
      setQuery("")
      await loadList()
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("communityDeleteError"))
    }
  }

  async function add(person: Person) {
    if (!selectedId || person.member) return
    setError("")
    try {
      await api.addMember(selectedId, person.id)
      setPeople((rows) => rows.map((item) => (item.id === person.id ? { ...item, member: true } : item)))
      setDetail(await api.community(selectedId))
      setCommunities((await api.communities()).results)
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("addError"))
    }
  }

  async function remove(person: Person) {
    if (!selectedId) return
    setError("")
    try {
      await api.removeMember(selectedId, person.id)
      setPeople((rows) => rows.map((item) => (item.id === person.id ? { ...item, member: false } : item)))
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

  return (
    <div className="communities-backdrop" onMouseDown={onClose}>
      <section
        className="communities-panel"
        role="dialog"
        aria-modal="true"
        aria-label={t("communities")}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <h2>{t("communities")}</h2>
          <button type="button" onClick={onClose}>{t("close")}</button>
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
                      setQuery("")
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
                <div className="communities-title">
                  <h3>{detail.name}</h3>
                  <button type="button" className="danger" onClick={() => void removeCommunity()}>{t("remove")}</button>
                </div>
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
                <h4>{t("students")}</h4>
                <MemberList
                  people={detail.students}
                  empty={t("noStudents")}
                  removeLabel={t("removeMember")}
                  onRemove={remove}
                  onTranslation={(person, enabled) => void setStudentTranslation(person, enabled)}
                  onPaste={(person, enabled) => void setStudentPaste(person, enabled)}
                />
                <h4>{t("teachers")}</h4>
                <MemberList people={detail.teachers} empty={t("noTeachers")} removeLabel={t("removeMember")} onRemove={remove} />
                <label>
                  {t("searchLabel")}
                  <input
                    aria-label={t("searchPeople")}
                    value={query}
                    placeholder={t("searchPlaceholder")}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </label>
                {searched !== "" && searched === query.trim() && people.length === 0 && (
                  <p className="note">{t("noAccounts")}</p>
                )}
                <ul className="people-results">
                  {people.map((person) => (
                    <li key={person.id}>
                      <span>
                        <strong>{person.display_name}</strong>
                        <small>{person.email} · {person.role === "teacher" ? t("teacher") : t("student")}</small>
                      </span>
                      <button type="button" disabled={person.member} onClick={() => void add(person)}>
                        {person.member ? t("alreadyIn") : t("add")}
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="note">{t("pickCommunity")}</p>
            )}
            {error && <p className="error">{error}</p>}
          </div>
        </div>
      </section>
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
  if (people.length === 0) return <p className="note">{empty}</p>
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
