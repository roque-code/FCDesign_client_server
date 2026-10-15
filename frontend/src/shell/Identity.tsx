import type { Account } from "../api"
import { useT } from "../i18n"

export function AccountIdentity({ account }: { account: Account }) {
  const t = useT()
  return (
    <>
      <div className="who">
        <span className="avatar" aria-hidden="true">
          {initials(account.display_name)}
        </span>
        <span className="who-name">{account.display_name}</span>
        <span className="who-role">{account.role === "teacher" ? t("teacher") : t("student")}</span>
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
      </div>
    </>
  )
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
