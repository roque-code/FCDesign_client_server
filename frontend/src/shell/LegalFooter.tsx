import { useT } from "../i18n"

export function LegalFooter() {
  const t = useT()
  return (
    <footer className="app-legal">
      {t("rights", { year: new Date().getFullYear() })}
    </footer>
  )
}
