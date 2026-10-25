import { useMemo } from "react"

import { type LabSolution } from "../api"
import { Composer } from "../compose/Composer"
import { spellText } from "../dialect"
import { LANGUAGE_LABELS, type ForeignLanguage } from "../foreign/keywords"
import { useLocale, useT, type MessageKey } from "../i18n"
import { BlockWorkspace } from "./BlockWorkspace"

const TOOL_LABEL: Record<string, MessageKey> = {
  codigo: "writeCode",
  diagrama: "composeTitle",
  bloques: "blocksTool",
}

export function SolutionCard({
  solution,
  title,
  kicker = "yourBuild",
}: {
  solution: LabSolution
  title: string
  kicker?: MessageKey
}) {
  const t = useT()
  const locale = useLocale()
  const label = TOOL_LABEL[solution.tool] ? t(TOOL_LABEL[solution.tool]) : solution.tool
  const incoming = useMemo(
    () => ({ name: title, source: solution.source, semicolons: true, token: 1 }),
    [title, solution.source],
  )
  const showCode = solution.tool === "codigo" || (solution.tool === "bloques" && !solution.blocks)
  return (
    <article className="answer-card">
      <p className="enunciado-kicker">{t(kicker)}</p>
      <h2>{label}</h2>
      {solution.tool === "bloques" && solution.blocks ? (
        <div className="answer-stage">
          <BlockWorkspace
            readOnly
            onCount={() => undefined}
            onState={() => undefined}
            restore={{ key: 1, state: solution.blocks }}
          />
        </div>
      ) : null}
      {solution.tool === "diagrama" ? (
        <div className="answer-stage">
          <Composer
            embedded
            isolated
            preview
            active
            incoming={incoming}
            onBack={() => undefined}
            onOpenInEditor={() => undefined}
          />
        </div>
      ) : null}
      {showCode ? <pre className="lab-code">{spellText(locale, solution.source)}</pre> : null}
      {solution.language ? (
        <>
          <h2>{LANGUAGE_LABELS[solution.language.language as ForeignLanguage] ?? solution.language.language}</h2>
          <p>{t("languageGrade", { percent: solution.language.percent })}</p>
          <pre className="lab-code">{solution.language.source}</pre>
        </>
      ) : null}
    </article>
  )
}
