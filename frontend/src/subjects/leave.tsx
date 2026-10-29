import { createContext, useContext, type ReactNode } from "react"

import { useT } from "../i18n"

const LeaveSubjectContext = createContext<(() => void) | null>(null)

export function LeaveSubjectProvider({ leave, children }: { leave: () => void; children: ReactNode }) {
  return <LeaveSubjectContext.Provider value={leave}>{children}</LeaveSubjectContext.Provider>
}

export function LeaveSubjectButton() {
  const leave = useContext(LeaveSubjectContext)
  const t = useT()
  if (!leave) return null
  return (
    <button className="top-action" type="button" onClick={leave}>
      {t("subjects")}
    </button>
  )
}
