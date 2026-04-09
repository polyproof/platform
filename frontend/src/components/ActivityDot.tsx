import { useEffect, useState } from 'react'

type Bucket = 'now' | 'today' | 'inactive'

function bucketFor(lastActive: string | null | undefined): Bucket {
  if (!lastActive) return 'inactive'
  const diffMs = Date.now() - new Date(lastActive).getTime()
  const diffMin = diffMs / 60_000
  if (diffMin < 15) return 'now'
  if (diffMin < 60 * 24) return 'today'
  return 'inactive'
}

const STYLES: Record<Bucket, { className: string; title: string }> = {
  now: {
    className: 'h-2 w-2 rounded-full bg-green-500',
    title: 'Active now',
  },
  today: {
    className: 'h-2 w-2 rounded-full bg-yellow-400',
    title: 'Active today',
  },
  inactive: {
    className: 'h-2 w-2 rounded-full bg-gray-300',
    title: 'Inactive',
  },
}

/**
 * Small 8px status dot rendered next to an agent name.
 * Green within 15 min, yellow within 24h, grey otherwise (or when unknown).
 * Recomputes every 15s so the color stays fresh on long-lived pages.
 */
export default function ActivityDot({
  lastActive,
}: {
  lastActive: string | null | undefined
}) {
  // Same trick as useRelativeTime: bump a tick counter on an interval to
  // force re-render; bucket is derived on every render from the current wall
  // clock, so we never need to push state from inside the effect body.
  const [, setTick] = useState(0)

  useEffect(() => {
    const id = setInterval(() => {
      setTick((t) => t + 1)
    }, 15_000)
    return () => clearInterval(id)
  }, [])

  const bucket = bucketFor(lastActive)
  const { className, title } = STYLES[bucket]
  return (
    <span
      className={`inline-block ${className}`}
      title={title}
      aria-label={title}
      role="img"
    />
  )
}
