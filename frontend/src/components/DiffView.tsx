// B35: self-contained word-level diff (LCS) — no external deps (offline/local constraint).
// Renders removals in red strikethrough and additions in green so "regenerate" is an informed
// choice, not a silent overwrite.

type Op = { type: 'same' | 'add' | 'del', text: string }

function tokenize(s: string): string[] {
  // Words + whitespace runs kept as tokens so the diff re-renders faithfully.
  return s.split(/(\s+)/).filter(t => t.length > 0)
}

function diffWords(a: string, b: string): Op[] {
  const A = tokenize(a), B = tokenize(b)
  // Cap the LCS table for very long chapters: fall back to block compare per paragraph.
  if (A.length * B.length > 4_000_000) {
    return a === b ? [{ type: 'same', text: a }] : [{ type: 'del', text: a }, { type: 'add', text: b }]
  }
  const n = A.length, m = B.length
  // LCS lengths (rolling rows to bound memory).
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0))
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = A[i] === B[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
    }
  }
  const ops: Op[] = []
  let i = 0, j = 0
  const push = (type: Op['type'], text: string) => {
    const last = ops[ops.length - 1]
    if (last && last.type === type) last.text += text
    else ops.push({ type, text })
  }
  while (i < n && j < m) {
    if (A[i] === B[j]) { push('same', A[i]); i++; j++ }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { push('del', A[i]); i++ }
    else { push('add', B[j]); j++ }
  }
  while (i < n) { push('del', A[i]); i++ }
  while (j < m) { push('add', B[j]); j++ }
  return ops
}

export default function DiffView({ oldText, newText }: { oldText: string, newText: string }) {
  const ops = diffWords(oldText, newText)
  return (
    <div className="text-sm whitespace-pre-wrap leading-relaxed bg-gray-950 border border-gray-800 rounded-lg p-3 max-h-96 overflow-y-auto">
      {ops.map((op, i) =>
        op.type === 'same' ? <span key={i}>{op.text}</span>
          : op.type === 'add' ? <span key={i} className="bg-green-900/50 text-green-200 rounded-sm">{op.text}</span>
            : <span key={i} className="bg-red-950/60 text-red-300/80 line-through decoration-red-500/50 rounded-sm">{op.text}</span>
      )}
    </div>
  )
}
