import type { PointerEvent as ReactPointerEvent } from "react"

/** `onStep` recibe un paso positivo con flecha arriba o derecha y negativo con abajo o izquierda. */
export function Splitter({
  axis,
  label,
  value,
  min,
  max,
  onPointerDown,
  onStep,
}: {
  axis: "x" | "y"
  label: string
  value: number
  min: number
  max: number
  onPointerDown: (event: ReactPointerEvent<HTMLButtonElement>) => void
  onStep: (delta: number) => void
}) {
  const [grow, shrink] = axis === "y" ? ["ArrowUp", "ArrowDown"] : ["ArrowRight", "ArrowLeft"]
  return (
    <button
      type="button"
      className={axis === "y" ? "splitter splitter-row" : "splitter"}
      role="separator"
      aria-orientation={axis === "y" ? "horizontal" : "vertical"}
      aria-label={label}
      aria-valuenow={value}
      aria-valuemin={min}
      aria-valuemax={max}
      onPointerDown={onPointerDown}
      onKeyDown={(event) => {
        const step = event.shiftKey ? 48 : 16
        if (event.key === grow) {
          event.preventDefault()
          onStep(step)
        }
        if (event.key === shrink) {
          event.preventDefault()
          onStep(-step)
        }
      }}
    />
  )
}
