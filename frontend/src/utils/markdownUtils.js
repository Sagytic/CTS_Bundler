/** Last ```abap``` or ``` ``` block from AI markdown (for SAP write). */
export function extractRefactoredCode(markdown) {
  if (!markdown || typeof markdown !== 'string') return ''
  const matches = [...(markdown.matchAll(/```(?:abap)?\s*([\s\S]*?)```/g) || [])]
  return matches.length ? matches[matches.length - 1][1].trim() : ''
}
