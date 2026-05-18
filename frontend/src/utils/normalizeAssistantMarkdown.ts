/**
 * Heuristic fixes for model output that uses inline bullets (e.g. "text * item * item")
 * so react-markdown + GFM can render real lists.
 */
export function normalizeAssistantMarkdown(text: string): string {
  let s = text.replace(/\r\n/g, '\n')

  // Colon / semicolon followed by bullet on same line
  s = s.replace(/:\s*\*\s+/g, ':\n* ')
  s = s.replace(/:\s*-\s+/g, ':\n- ')
  s = s.replace(/;\s*\*\s+/g, ';\n* ')

  // Mid-line * bullets (avoid **bold** — require space before * and after)
  s = s.replace(/([^\n*])\s+\*\s+(?=\S)/g, '$1\n* ')

  // Mid-line - bullets (require spaces around '-')
  s = s.replace(/([^\n-])\s+-\s+(?=\S)/g, '$1\n- ')

  // Bullet character
  s = s.replace(/([^\n])\s+•\s+/g, '$1\n• ')

  return s
}
