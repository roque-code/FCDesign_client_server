import { type Account } from "../api"
import { useT } from "../i18n"
import { AccountIdentity } from "./Identity"
import { Logo } from "./Logo"

export function AccountOnly({
  account,
  onAccount,
  onLogout,
}: {
  account: Account
  onAccount: (account: Account) => void
  onLogout: () => void
}) {
  const t = useT()
  const plan = account.plan
  return (
    <div className="shell">
      <header className="topbar topbar-editor">
        <div className="brand">
          <h1><Logo /></h1>
          <AccountIdentity account={account} onAccount={onAccount} />
        </div>
        <div className="actions">
          <button className="top-leave" type="button" onClick={onLogout}>
            {t("leave")}
          </button>
        </div>
      </header>
      <main className="account-only">
        <section className="card account-card">
          <h2>{t("accountOnlyTitle")}</h2>
          <p className="note">{t("accountOnlyNote")}</p>
          <dl className="account-facts">
            <div>
              <dt>{t("profile")}</dt>
              <dd>{account.role === "teacher" ? t("teacher") : t("student")}</dd>
            </div>
            <div>
              <dt>{t("planWord")}</dt>
              <dd>
                {plan ? plan.name : t("noPlan")}
                {plan?.status === "expired" ? ` · ${t("expired")}` : ""}
              </dd>
            </div>
            <div>
              <dt>{t("payment")}</dt>
              <dd>{paymentLine(plan, t)}</dd>
            </div>
          </dl>
        </section>
      </main>
    </div>
  )
}

function paymentLine(
  plan: Account["plan"],
  t: (key: "daysLeft" | "noPaymentDue" | "expired", vars?: { days: number }) => string,
): string {
  if (!plan || plan.days_remaining === null) return t("noPaymentDue")
  if (plan.status === "expired" || plan.days_remaining === 0) return t("expired")
  return t("daysLeft", { days: plan.days_remaining })
}
