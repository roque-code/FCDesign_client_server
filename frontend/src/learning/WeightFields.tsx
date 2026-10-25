import { useT, type MessageKey } from "../i18n"
import { WEIGHT_KEYS, weightTotal, type LabWeights, type WeightKey } from "./weights"

const LABELS: Record<WeightKey, MessageKey> = {
  comprension: "weightUnderstand",
  diseno: "weightReason",
  correccion: "weightCorrect",
  lenguaje: "weightLanguage",
  explicacion: "weightExplain",
  autonomia: "weightAutonomy",
}

export function WeightFields({
  activity,
  weights,
  onChange,
  note,
}: {
  activity: string
  weights: LabWeights
  onChange: (weights: LabWeights) => void
  note?: string
}) {
  const t = useT()
  const total = weightTotal(weights)
  const keys = WEIGHT_KEYS.filter((key) => key !== "lenguaje" || activity === "build")

  function setValue(key: WeightKey, raw: string) {
    const value = raw === "" ? 0 : Number(raw)
    if (!Number.isFinite(value)) return
    onChange({ ...weights, [key]: Math.max(0, Math.min(100, Math.round(value))) })
  }

  return (
    <fieldset className="weight-fields">
      <legend>{t("weightRubric")}</legend>
      <p>{note ?? t("weightNote")}</p>
      <div className="weight-grid">
        {keys.map((key) => (
          <label key={key}>
            {t(LABELS[key])}
            <input
              type="number"
              min={0}
              max={100}
              value={weights[key]}
              onChange={(event) => setValue(key, event.target.value)}
            />
          </label>
        ))}
      </div>
      <p className={total === 100 ? "note" : "error"}>{t("weightTotal", { total })}</p>
    </fieldset>
  )
}
