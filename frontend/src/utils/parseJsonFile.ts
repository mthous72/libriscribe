// Verbose JSON parsing for user-supplied import files.
//
// JSON.parse errors are terse and position-only; for a 100 KB lore file that's useless.
// This wrapper tolerates a UTF-8 BOM (Windows editors add one; JSON.parse rejects it) and
// rethrows SyntaxErrors enriched with line/column plus a marked snippet around the failure.

export function parseJsonVerbose(raw: string): any {
  const text = raw.replace(/^﻿/, '')
  try {
    return JSON.parse(text)
  } catch (err: any) {
    throw new SyntaxError(describeJsonError(text, err))
  }
}

function describeJsonError(text: string, err: any): string {
  const msg = String(err?.message || 'Invalid JSON')
  if (!text.trim()) return 'Invalid JSON: the file is empty.'

  let pos = -1
  const mPos = msg.match(/position (\d+)/)
  const mLC = msg.match(/line (\d+) column (\d+)/)
  if (mPos) {
    pos = parseInt(mPos[1], 10)
  } else if (mLC) {
    const lines = text.split('\n')
    pos = lines.slice(0, parseInt(mLC[1], 10) - 1).reduce((n, l) => n + l.length + 1, 0)
      + parseInt(mLC[2], 10) - 1
  }

  if (pos < 0 || pos > text.length) return `Invalid JSON: ${msg}`

  const upTo = text.slice(0, pos)
  const line = upTo.split('\n').length
  const col = pos - upTo.lastIndexOf('\n')
  const start = Math.max(0, pos - 60)
  const end = Math.min(text.length, pos + 60)
  const snippet = (text.slice(start, pos) + ' ⟵HERE⟶ ' + text.slice(pos, end)).replace(/\n/g, '⏎')
  return `Invalid JSON at line ${line}, column ${col}: ${msg}\n\n…${snippet}…`
}
