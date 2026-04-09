import { useEffect, useState } from 'react'

// Compute a relative-time string from a date string.
// - <1 min  → "just now"
// - <60 min → "Nm ago"
// - <24 h   → "Nh ago"
// - <30 d   → "Nd ago"
// - older   → absolute date ("Jan 5, 2026")
function computeRelative(dateStr: string): string {
  const then = new Date(dateStr).getTime()
  const diffMs = Date.now() - then
  const diffMin = Math.floor(diffMs / 60_000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHrs = Math.floor(diffMin / 60)
  if (diffHrs < 24) return `${diffHrs}h ago`
  const diffDays = Math.floor(diffHrs / 24)
  if (diffDays < 30) return `${diffDays}d ago`
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

/**
 * Returns a relative-time string that re-computes every 15 seconds so
 * timestamps stay fresh without a full page refresh.
 *
 * Returns `null` if the input is null/undefined — callers decide how to render
 * a missing value (e.g. "never", "—", or simply hide the element).
 */
export function useRelativeTime(dateStr: string | null | undefined): string | null {
  // `tick` is bumped every 15s to force a re-render so the derived string
  // below stays fresh. We don't store the string in state — deriving it each
  // render avoids cascading setState-in-effect patterns and keeps the hook
  // trivially correct when `dateStr` changes.
  const [, setTick] = useState(0)

  useEffect(() => {
    if (!dateStr) return
    const id = setInterval(() => {
      setTick((t) => t + 1)
    }, 15_000)
    return () => clearInterval(id)
  }, [dateStr])

  return dateStr ? computeRelative(dateStr) : null
}

export default useRelativeTime
