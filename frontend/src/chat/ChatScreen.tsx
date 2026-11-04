import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react"

import { api, ApiError, type Account, type ChatGroupOption, type ChatMessage } from "../api"
import { translate, translatedMessage, useLocale, useT, type Locale } from "../i18n"
import { AccountIdentity } from "../shell/Identity"
import { Logo } from "../shell/Logo"
import { SUBJECTS, type SubjectId } from "../subjects/catalog"

function stamp(value: string, locale: Locale): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleString(locale === "en" ? "en" : "es", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function preview(message: ChatMessage | null): string {
  if (!message) return ""
  return message.body.replace(/\s+/g, " ").trim()
}

export function ChatScreen({
  account,
  onAccount,
  onBack,
}: {
  account: Account
  onAccount: (account: Account) => void
  onBack: () => void
}) {
  const t = useT()
  const locale = useLocale()
  const [subject, setSubject] = useState<SubjectId>("fundamentos")
  const [groups, setGroups] = useState<ChatGroupOption[]>([])
  const [hours, setHours] = useState<number | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [groupId, setGroupId] = useState("")
  const [query, setQuery] = useState("")
  const [target, setTarget] = useState<"group" | number>("group")
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState("")
  const [sending, setSending] = useState(false)
  const [error, setError] = useState("")
  const logRef = useRef<HTMLDivElement>(null)
  const stickRef = useRef(true)

  useEffect(() => {
    let ignore = false
    async function load() {
      try {
        const page = await api.chatBoard(subject)
        if (ignore) return
        setGroups(page.groups)
        setHours(page.hours)
        setLoaded(true)
        setGroupId((current) => {
          if (current && page.groups.some((item) => item.id === current)) return current
          return page.groups[0]?.id ?? ""
        })
      } catch (caught) {
        if (ignore) return
        setError(caught instanceof ApiError ? translatedMessage(caught.message) : translate(locale, "chatLoadError"))
      }
    }
    void load()
    const timer = window.setInterval(() => {
      void load()
    }, 5000)
    return () => {
      ignore = true
      window.clearInterval(timer)
    }
  }, [subject, locale])

  useEffect(() => {
    if (!loaded) return
    const chosen = groups.find((item) => item.id === groupId)
    if (!groupId || !chosen) {
      if (groups.length === 0) return
      setGroupId(groups[0].id)
      setTarget("group")
      return
    }
    if (target !== "group" && !chosen.people.some((person) => person.id === target)) {
      setTarget("group")
      setError(translate(locale, "chatPeerLeft"))
    }
  }, [groups, groupId, target, loaded, locale])

  useEffect(() => {
    if (!groupId) {
      setConversationId(null)
      setMessages([])
      return
    }
    let ignore = false
    async function open() {
      stickRef.current = true
      try {
        const thread = await api.openChat(subject, groupId, target === "group" ? null : target)
        if (ignore) return
        setError("")
        setConversationId(thread.id)
        setMessages(thread.messages)
        setGroups((current) =>
          current.map((group) => {
            if (group.id !== groupId) return group
            if (target === "group") return { ...group, unread: 0 }
            return {
              ...group,
              people: group.people.map((person) => (person.id === target ? { ...person, unread: 0 } : person)),
            }
          }),
        )
      } catch (caught) {
        if (ignore) return
        setConversationId(null)
        setMessages([])
        setError(caught instanceof ApiError ? translatedMessage(caught.message) : translate(locale, "chatLoadError"))
      }
    }
    void open()
    return () => {
      ignore = true
    }
  }, [subject, groupId, target, locale])

  useEffect(() => {
    if (!conversationId) return
    let ignore = false
    async function load() {
      try {
        const page = await api.chatMessages(conversationId as string)
        if (!ignore) setMessages(page.results)
      } catch (caught) {
        if (ignore) return
        setError(caught instanceof ApiError ? translatedMessage(caught.message) : translate(locale, "chatLoadError"))
      }
    }
    const timer = window.setInterval(() => {
      void load()
    }, 4000)
    return () => {
      ignore = true
      window.clearInterval(timer)
    }
  }, [conversationId, locale])

  useEffect(() => {
    const el = logRef.current
    if (!el || !stickRef.current) return
    el.scrollTop = el.scrollHeight
  }, [messages, conversationId])

  const chosen = groups.find((item) => item.id === groupId) ?? null
  const person = chosen && target !== "group" ? chosen.people.find((item) => item.id === target) ?? null : null
  const subjectName = t(SUBJECTS.find((item) => item.id === subject)?.nameKey ?? "subjectFundamentos")
  const destination = target === "group" ? t("chatWholeGroup") : person?.display_name ?? t("chatWholeGroup")
  const lifetime = hours == null ? "" : hours === 1 ? t("chatLifetimeOne") : t("chatLifetime", { hours })

  async function send(event?: FormEvent) {
    event?.preventDefault()
    const body = draft.trim()
    if (!conversationId || !body || sending) return
    setSending(true)
    setError("")
    try {
      await api.sendChatMessage(conversationId, body)
      setDraft("")
      stickRef.current = true
      const page = await api.chatMessages(conversationId)
      setMessages(page.results)
      const board = await api.chatBoard(subject)
      setGroups(board.groups)
      setHours(board.hours)
    } catch (caught) {
      setError(caught instanceof ApiError ? translatedMessage(caught.message) : t("chatLoadError"))
    } finally {
      setSending(false)
    }
  }

  function onDraftKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      void send()
    }
  }

  function chooseGroup(next: string) {
    setError("")
    setQuery("")
    setGroupId(next)
    setTarget("group")
  }

  const needle = query.trim().toLocaleLowerCase()
  const visiblePeople = chosen
    ? chosen.people.filter((person) => {
        if (needle) return person.display_name.toLocaleLowerCase().includes(needle)
        return person.unread > 0 || person.id === target
      })
    : []
  const hiddenPeople = chosen
    ? chosen.people.filter((person) => person.unread === 0 && person.id !== target).length
    : 0

  return (
    <div className="shell chat-screen">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1>
            <Logo mark />
            {t("chat")}
          </h1>
          <AccountIdentity account={account} onAccount={onAccount} />
        </div>
        <div className="actions">
          <button className="top-leave" type="button" onClick={onBack}>
            {t("backToSubjects")}
          </button>
        </div>
      </header>
      <div className="chat-body">
        <aside className="chat-people">
          <p className="note">{t("chatLead")}</p>
          <label>
            {t("chatSubject")}
            <select
              value={subject}
              onChange={(event) => {
                setError("")
                setQuery("")
                setGroups([])
                setLoaded(false)
                setGroupId("")
                setTarget("group")
                setConversationId(null)
                setMessages([])
                setSubject(event.target.value as SubjectId)
              }}
            >
              {SUBJECTS.map((item) => (
                <option key={item.id} value={item.id}>
                  {t(item.nameKey)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("chatGroup")}
            <select value={groupId} onChange={(event) => chooseGroup(event.target.value)} disabled={groups.length === 0}>
              {groups.length === 0 ? <option value="">{t("chatEmptyGroups")}</option> : null}
              {groups.map((item) => {
                const pending = item.unread + item.people.filter((person) => person.unread > 0).length
                return (
                  <option key={item.id} value={item.id}>
                    {pending > 0 ? `${item.name} (${pending})` : item.name}
                  </option>
                )
              })}
            </select>
          </label>
          {chosen && chosen.people.length > 0 ? (
            <label>
              {t(account.role === "teacher" ? "chatSearchStudent" : "chatSearchTeacher")}
              <input value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
          ) : null}
          {error && !chosen ? <p className="error">{error}</p> : null}
          {chosen ? (
            <ul>
              <li>
                <button
                  type="button"
                  className="chat-person"
                  aria-pressed={target === "group"}
                  onClick={() => {
                    setError("")
                    setTarget("group")
                  }}
                >
                  <span className="chat-person-name">
                    <strong>{t("chatWholeGroup")}</strong>
                    {chosen.unread > 0 ? <span className="chat-unread">{chosen.unread}</span> : null}
                  </span>
                  <span>{chosen.name}</span>
                  {chosen.last_message ? (
                    <span className="chat-preview">
                      {preview(chosen.last_message)}
                      {chosen.last_message.created_at ? ` · ${stamp(chosen.last_message.created_at, locale)}` : ""}
                    </span>
                  ) : null}
                </button>
              </li>
              {visiblePeople.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="chat-person"
                    aria-pressed={item.id === target}
                    onClick={() => {
                      setError("")
                      setTarget(item.id)
                    }}
                  >
                    <span className="chat-person-name">
                      <strong>{item.display_name}</strong>
                      {item.unread > 0 ? <span className="chat-unread">{item.unread}</span> : null}
                    </span>
                    <span>{chosen.name}</span>
                    {item.last_message ? (
                      <span className="chat-preview">
                        {preview(item.last_message)}
                        {item.last_message.created_at ? ` · ${stamp(item.last_message.created_at, locale)}` : ""}
                      </span>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {chosen && !needle && hiddenPeople > 0 ? <p className="note">{t("chatUnreadHint")}</p> : null}
          {chosen && needle && visiblePeople.length === 0 ? <p className="note">{t("chatNoMatch")}</p> : null}
          {loaded && groups.length === 0 ? (
            <p className="note">{t(account.role === "teacher" ? "chatEmptyTeacher" : "chatEmptyStudent")}</p>
          ) : null}
        </aside>
        <section className="chat-thread" aria-label={chosen ? `${chosen.name} ${destination}` : t("chat")}>
          {chosen ? (
            <>
              <header className="chat-thread-head">
                <h2>{target === "group" ? t("chatWholeGroup") : destination}</h2>
                <p className="note">
                  {subjectName} · {chosen.name}
                </p>
                {lifetime ? <p className="note">{lifetime}</p> : null}
              </header>
              <div
                className="chat-log"
                ref={logRef}
                onScroll={() => {
                  const el = logRef.current
                  if (!el) return
                  stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80
                }}
              >
                {messages.length === 0 ? <p className="chat-empty">{t("chatNoMessages")}</p> : null}
                {messages.map((message) => (
                  <article
                    key={message.id}
                    className={message.sender_id === account.id ? "chat-bubble mine" : "chat-bubble"}
                  >
                    {message.sender_id === account.id ? null : <strong>{message.sender_name}</strong>}
                    <p>{message.body}</p>
                    <time dateTime={message.created_at}>{stamp(message.created_at, locale)}</time>
                  </article>
                ))}
              </div>
              <form className="chat-composer" onSubmit={(event) => void send(event)}>
                {error ? <p className="error">{error}</p> : null}
                <label>
                  {t("chatPlaceholder")}
                  <textarea
                    value={draft}
                    maxLength={2000}
                    rows={3}
                    onChange={(event) => setDraft(event.target.value)}
                    onKeyDown={onDraftKey}
                  />
                </label>
                <div className="chat-composer-row">
                  <p className="note">{t("chatSendHint")}</p>
                  <button className="primary" type="submit" disabled={!conversationId || !draft.trim() || sending}>
                    {t("chatSend")}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <p className="chat-empty">{t("chatPick")}</p>
          )}
        </section>
      </div>
    </div>
  )
}
