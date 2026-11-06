import { renderPrompt } from "./promptMarkdown"

export function PromptText({ text }: { text: string }) {
  if (!text.trim()) return null
  return <div className="enunciado-text prompt-doc" dangerouslySetInnerHTML={{ __html: renderPrompt(text) }} />
}
