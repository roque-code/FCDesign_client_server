import { useEffect, useRef, useState, type FormEvent } from "react"

import { api, ApiError, type Community, type CommunitySummary, type Person } from "../api"
import { useT } from "../i18n"

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
  const selectedRef = useRef(selectedId)
  selectedRef.current = selectedId

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
    let alive = true
    async function pull() {
      if (document.visibilityState === "hidden") return
      const page = await api.communities()
      if (!alive) return
      setCommunities(page.results)
      const current = selectedRef.current
      const next = current && page.results.some((item) => item.id === current) ? current : page.results[0]?.id ?? ""
      setSelectedId(next)
      if (!next) {
        setDetail(null)
        return
      }
      const item = await api.community(next)
      if (alive && selectedRef.current === next) setDetail(item)
    }
    void pull().catch((caught: unknown) => {
      setError(caught instanceof ApiError ? caught.message : t("communitiesLoadError"))
    })
    const timer = window.setInterval(() => {
      void pull().catch(() => undefined)
    }, 5000)
    const onShow = () => {
      void pull().catch(() => undefined)
    }
    document.addEventListener("visibilitychange", onShow)
    return () => {
      alive = false
      window.clearInterval(timer)
      document.removeEventListener("visibilitychange", onShow)
    }
  }, [])

  useEffect(() => {
    if (!selectedId) return
    let alive = true
    void api.community(selectedId).then((item) => {
      if (alive) setDetail(item)
    }).catch((caught: unknown) => {
      if (alive) setError(caught instanceof ApiError ? caught.message : t("communityOpenError"))
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
        setError(caught instanceof ApiError ? caught.message : t("searchError"))
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
      setError(caught instanceof ApiError ? caught.message : t("communityCreateError"))
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
      setError(caught instanceof ApiError ? caught.message : t("communityDeleteError"))
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
      setError(caught instanceof ApiError ? caught.message : t("addError"))
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
      setError(caught instanceof ApiError ? caught.message : t("removeError"))
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
                    <span>{t("studentCount", { count: item.student_count })}</span>
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
                <h4>{t("students")}</h4>
                <MemberList people={detail.students} empty={t("noStudents")} removeLabel={t("removeMember")} onRemove={remove} />
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
}: {
  people: Person[]
  empty: string
  removeLabel: string
  onRemove: (person: Person) => void
}) {
  if (people.length === 0) return <p className="note">{empty}</p>
  return (
    <ul className="member-list">
      {people.map((person) => (
        <li key={person.id}>
          <span>
            <strong>{person.display_name}</strong>
            <small>{person.email}</small>
          </span>
          <button type="button" className="danger" onClick={() => onRemove(person)}>{removeLabel}</button>
        </li>
      ))}
    </ul>
  )
}
