import { useRef, useState } from "react"

import { accessOf, ApiError, api, type Account } from "../api"
import { useT } from "../i18n"

export function AccountIdentity({
  account,
  onAccount,
}: {
  account: Account
  onAccount?: (account: Account) => void
}) {
  const t = useT()
  const [open, setOpen] = useState(false)
  const runLimit = accessOf(account).limits.max_executions_per_day
  const runsUsed = account.usage?.executions_today ?? 0
  const runsLeft = runLimit == null ? null : Math.max(0, runLimit - runsUsed)
  const runsTitle =
    runsLeft == null
      ? t("unlimitedRuns")
      : runsLeft === 0
        ? t("executionsGone")
        : runsLeft === 1
          ? t("executionsLeftOne")
          : t("executionsLeft", { count: runsLeft })
  return (
    <>
      <div className="who">
        <button
          className="avatar avatar-button"
          type="button"
          aria-label={t("customizeProfile")}
          onClick={() => setOpen(true)}
        >
          {account.avatar ? <img src={account.avatar} alt="" /> : initials(account.display_name)}
        </button>
        <span className="who-name">{account.display_name}</span>
        <span className="who-role">
          {account.role === "teacher" ? t("teacher") : account.role === "admin" ? t("administrator") : t("student")}
          {account.plan ? ` · ${account.plan.name}` : ""}
          {account.plan?.status === "expired" ? ` · ${t("expired")}` : ""}
        </span>
      </div>
      <div className="standing">
        <span className="stat" title={t("pointsTitle", { points: account.points })}>
          <PointsMark points={account.points} />
          <strong>{account.points}</strong>
          <small>{t("points")}</small>
        </span>
        <span className="stat" title={t("rankTitle", { rank: account.rank })}>
          <RankMark rank={account.rank} />
          <strong>{account.rank}</strong>
          <small>{t("place")}</small>
        </span>
        {account.plan?.days_remaining !== null && account.plan ? (
          <span className="stat" title={t("daysLeft", { days: account.plan.days_remaining })}>
            <DaysMark days={account.plan.days_remaining} />
            <strong>{account.plan.days_remaining}</strong>
            <small>{t("daysShort")}</small>
          </span>
        ) : null}
        <span className="stat" title={runsTitle}>
          <RunsMark left={runsLeft} />
          <strong>{runsLeft == null ? "∞" : runsLeft}</strong>
          <small>{t("runsShort")}</small>
        </span>
      </div>
      {open ? (
        <ProfileDialog
          account={account}
          onClose={() => setOpen(false)}
          onAccount={(next) => {
            onAccount?.(next)
            setOpen(false)
          }}
        />
      ) : null}
    </>
  )
}

function ProfileDialog({
  account,
  onClose,
  onAccount,
}: {
  account: Account
  onClose: () => void
  onAccount: (account: Account) => void
}) {
  const t = useT()
  const fileRef = useRef<HTMLInputElement>(null)
  const [name, setName] = useState(account.display_name)
  const [avatar, setAvatar] = useState<string | null>(account.avatar)
  const [currentPassword, setCurrentPassword] = useState("")
  const [password, setPassword] = useState("")
  const [repeat, setRepeat] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  async function choosePhoto(file: File | undefined) {
    if (!file) return
    setError("")
    try {
      setAvatar(await squarePhoto(file))
    } catch {
      setError(t("photoError"))
    }
  }

  async function save() {
    if (password !== repeat) {
      setError(t("passwordMismatch"))
      return
    }
    setBusy(true)
    setError("")
    try {
      const next = await api.updateAccount({
        display_name: name.trim(),
        avatar,
        ...(password ? { current_password: currentPassword, password } : {}),
      })
      onAccount(next)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("profileSaveError"))
      setBusy(false)
    }
  }

  return (
    <div
      className="profile-dialog"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <form
        className="profile-card"
        role="dialog"
        aria-label={t("customizeProfile")}
        onSubmit={(event) => {
          event.preventDefault()
          void save()
        }}
      >
        <header>
          <h2>{t("customizeProfile")}</h2>
          <button type="button" onClick={onClose}>
            {t("close")}
          </button>
        </header>
        <div className="profile-photo">
          <span className="avatar" aria-hidden="true">
            {avatar ? <img src={avatar} alt="" /> : initials(name)}
          </span>
          <div>
            <p>{t("profilePhoto")}</p>
            <p className="note">{t("photoHint")}</p>
            <div className="profile-photo-actions">
              <button type="button" onClick={() => fileRef.current?.click()}>
                {t("choosePhoto")}
              </button>
              {avatar ? (
                <button type="button" onClick={() => setAvatar(null)}>
                  {t("removePhoto")}
                </button>
              ) : null}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              onChange={(event) => {
                void choosePhoto(event.target.files?.[0])
                event.target.value = ""
              }}
            />
          </div>
        </div>
        <label>
          {t("nameWord")}
          <input value={name} maxLength={80} required onChange={(event) => setName(event.target.value)} />
        </label>
        <fieldset>
          <legend>{t("password")}</legend>
          <p className="note">{t("passwordHint")}</p>
          <label>
            {t("currentPassword")}
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
            />
          </label>
          <label>
            {t("newPassword")}
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <label>
            {t("repeatPassword")}
            <input
              type="password"
              autoComplete="new-password"
              value={repeat}
              onChange={(event) => setRepeat(event.target.value)}
            />
          </label>
        </fieldset>
        {error ? <p className="error">{error}</p> : null}
        <div className="profile-actions">
          <button type="button" onClick={onClose} disabled={busy}>
            {t("cancel")}
          </button>
          <button className="primary" type="submit" disabled={busy}>
            {t("save")}
          </button>
        </div>
      </form>
    </div>
  )
}

async function squarePhoto(file: File): Promise<string> {
  if (!file.type.startsWith("image/") || file.type === "image/svg+xml" || file.size > 8_000_000) {
    throw new Error("photo")
  }
  const bitmap = await createImageBitmap(file)
  const side = 256
  const scale = Math.max(side / bitmap.width, side / bitmap.height)
  const canvas = document.createElement("canvas")
  canvas.width = side
  canvas.height = side
  const context = canvas.getContext("2d")
  if (!context) throw new Error("photo")
  context.fillStyle = "#ffffff"
  context.fillRect(0, 0, side, side)
  context.drawImage(
    bitmap,
    (side - bitmap.width * scale) / 2,
    (side - bitmap.height * scale) / 2,
    bitmap.width * scale,
    bitmap.height * scale,
  )
  bitmap.close()
  let quality = 0.86
  let url = canvas.toDataURL("image/jpeg", quality)
  while (url.length > 150_000 && quality > 0.45) {
    quality -= 0.1
    url = canvas.toDataURL("image/jpeg", quality)
  }
  if (!url.startsWith("data:image/jpeg;base64,") || url.length > 160_000) throw new Error("photo")
  return url
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  const letters = parts.slice(0, 2).map((part) => part[0] ?? "")
  return letters.join("").toLocaleUpperCase("es") || "?"
}

function pointsTier(points: number): "none" | "spark" | "star" | "bolt" | "crown" {
  if (points <= 0) return "none"
  if (points < 30) return "spark"
  if (points < 100) return "star"
  if (points < 250) return "bolt"
  return "crown"
}

function rankTier(rank: number): "gold" | "silver" | "bronze" | "place" {
  if (rank === 1) return "gold"
  if (rank === 2) return "silver"
  if (rank === 3) return "bronze"
  return "place"
}

function PointsMark({ points }: { points: number }) {
  const tier = pointsTier(points)
  return (
    <svg className={`mark mark-${tier}`} viewBox="0 0 24 24" aria-hidden="true">
      {tier === "none" && <circle cx="12" cy="12" r="6.2" fill="none" stroke="currentColor" strokeWidth="1.8" />}
      {tier === "spark" && <path d="M12 1.8 13.7 8.1 20.2 10 13.7 11.9 12 18.2 10.3 11.9 3.8 10 10.3 8.1 12 1.8Z" />}
      {tier === "star" && <path d="M12 2.2 14.3 7l5.2.7-3.8 3.6.9 5.2L12 14.1 7.4 16.5l.9-5.2L4.5 7.7 9.7 7 12 2.2Z" />}
      {tier === "bolt" && <path d="M13.4 1.6 4.4 13.4h6.4l-1.2 9 9.8-12.6h-6.6l.6-8.2Z" />}
      {tier === "crown" && <path d="M3.4 17.8 5.2 8.4 9.3 12.6 12 4.8 14.7 12.6 18.8 8.4 20.6 17.8H3.4Zm.4 2.2h16.4v1.6H3.8v-1.6Z" />}
    </svg>
  )
}

function daysTier(days: number): "gone" | "low" | "open" {
  if (days <= 0) return "gone"
  if (days <= 7) return "low"
  return "open"
}

function runsTier(left: number | null): "gone" | "low" | "open" | "free" {
  if (left == null) return "free"
  if (left <= 0) return "gone"
  if (left <= 2) return "low"
  return "open"
}

function DaysMark({ days }: { days: number }) {
  return (
    <svg className={`mark mark-days-${daysTier(days)}`} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8.1 2.2h1.5v2.4H8.1V2.2Zm6.3 0h1.5v2.4h-1.5V2.2Z" />
      <path d="M6.4 4.8h1.1v1.5h9V4.8h1.1c1.15 0 2.1.95 2.1 2.1v11.2c0 1.15-.95 2.1-2.1 2.1H6.4c-1.15 0-2.1-.95-2.1-2.1V6.9c0-1.15.95-2.1 2.1-2.1Zm12 5.6H5.6v7.5c0 .44.36.8.8.8h11.2c.44 0 .8-.36.8-.8v-7.5Z" />
      <path d="M5.6 7.2h12.8v2.15H5.6V7.2Z" />
    </svg>
  )
}

function RunsMark({ left }: { left: number | null }) {
  return (
    <svg className={`mark mark-runs-${runsTier(left)}`} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8.3" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M10.15 8.05v7.9l6.85-3.95-6.85-3.95Z" />
    </svg>
  )
}

function RankMark({ rank }: { rank: number }) {
  const tier = rankTier(rank)
  return (
    <svg className={`mark mark-${tier}`} viewBox="0 0 24 24" aria-hidden="true">
      {tier === "place" ? (
        <path d="M3 20V12h5v8H3Zm6.5 0V7h5v13h-5ZM16 20v-6h5v6h-5Z" />
      ) : (
        <>
          <path d="M8.1 2h2.4L12 7.2 13.5 2h2.4L13.6 9.1h-3.2L8.1 2Z" />
          <circle cx="12" cy="15.2" r="5.3" />
        </>
      )}
    </svg>
  )
}
