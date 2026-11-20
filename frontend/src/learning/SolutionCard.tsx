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
  preferSource = false,
}: {
  solution: LabSolution
  title: string
  kicker?: MessageKey
  preferSource?: boolean
}) {
  const t = useT()
  const locale = useLocale()
  const label = TOOL_LABEL[solution.tool] ? t(TOOL_LABEL[solution.tool]) : solution.tool
  const incoming = useMemo(
    () => ({ name: title, source: solution.source, semicolons: true, token: 1 }),
    [title, solution.source],
  )
  const hasSource = Boolean(solution.source?.trim())
  const showCode = preferSource
    ? hasSource
    : solution.tool === "codigo" || (solution.tool === "bloques" && !solution.blocks)
  const blockState = solution.blocks
  const showBlocks = solution.tool === "bloques" && blockState != null && !(preferSource && hasSource)
  const showDiagram = solution.tool === "diagrama" && !(preferSource && hasSource)
  return (
    <article className="answer-card">
      <p className="enunciado-kicker">{t(kicker)}</p>
      <h2>{preferSource && hasSource ? t("pseudocode") : label}</h2>
      {showBlocks && blockState ? (
        <div className="answer-stage">
          <BlockWorkspace
            readOnly
            onCount={() => undefined}
            onState={() => undefined}
            restore={{ key: 1, state: blockState }}
          />
        </div>
      ) : null}
      {showDiagram ? (
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
