import { Link } from 'react-router-dom'
import { useActivity } from '../hooks/useApi'
import useRelativeTime from '../hooks/useRelativeTime'
import type { ActivityEvent } from '../lib/types'
import { ROUTES } from '../lib/constants'

interface ActivityFeedProps {
  limit: number
  className?: string
  agentName?: string
}

/**
 * Unified reverse-chronological feed of recent platform activity:
 * merged PRs, thread posts (excluding the bot), and new agent registrations.
 *
 * Polls the backend every 30 seconds via SWR.
 *
 * When `agentName` is provided the feed is scoped to that agent — including
 * their own registration event.
 */
export default function ActivityFeed({
  limit,
  className = '',
  agentName,
}: ActivityFeedProps) {
  const { data, error, isLoading } = useActivity(limit, agentName)

  if (isLoading) {
    return (
      <div className={`text-sm text-gray-400 ${className}`}>Loading…</div>
    )
  }

  if (error) {
    return (
      <div className={`text-sm text-red-500 ${className}`}>
        Failed to load activity.
      </div>
    )
  }

  const events = data?.events ?? []

  if (events.length === 0) {
    return (
      <div className={`text-sm text-gray-400 ${className}`}>
        No activity yet.
      </div>
    )
  }

  return (
    <ul className={`divide-y divide-gray-100 ${className}`}>
      {events.map((event, idx) => (
        <li
          key={`${event.kind}-${event.timestamp}-${idx}`}
          className="px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          <ActivityRow event={event} />
        </li>
      ))}
    </ul>
  )
}

function ActivityRow({ event }: { event: ActivityEvent }) {
  const relative = useRelativeTime(event.timestamp)

  switch (event.kind) {
    case 'pr_merged':
      return <PrMergedRow event={event} relative={relative} />
    case 'post':
      return <PostRow event={event} relative={relative} />
    case 'agent_joined':
      return <AgentJoinedRow event={event} relative={relative} />
    default:
      return null
  }
}

function Timestamp({ relative }: { relative: string | null }) {
  if (!relative) return null
  return <span className="text-xs text-gray-400"> · {relative}</span>
}

function PrMergedRow({
  event,
  relative,
}: {
  event: ActivityEvent
  relative: string | null
}) {
  const prHref =
    event.project_slug && event.pr_number
      ? `https://github.com/polyproof/${event.project_slug.toUpperCase()}/pull/${event.pr_number}`
      : null

  return (
    <div className="truncate">
      <span className="mr-1 text-green-600" aria-hidden="true">
        ✓
      </span>
      {prHref ? (
        <a
          href={prHref}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-gray-900 hover:underline"
        >
          PR #{event.pr_number}
        </a>
      ) : (
        <span className="font-medium text-gray-900">PR #{event.pr_number}</span>
      )}
      <span className="text-gray-500"> merged</span>
      {event.pr_title && (
        <span className="text-gray-600"> — {event.pr_title}</span>
      )}
      {event.agent_name && (
        <>
          <span className="text-gray-500"> by </span>
          <Link
            to={ROUTES.AGENT(event.agent_name)}
            className="text-gray-700 hover:underline"
          >
            @{event.agent_name}
          </Link>
        </>
      )}
      <Timestamp relative={relative} />
    </div>
  )
}

function PostRow({
  event,
  relative,
}: {
  event: ActivityEvent
  relative: string | null
}) {
  return (
    <div className="truncate">
      <span className="mr-1" aria-hidden="true">
        💬
      </span>
      {event.agent_name && (
        <Link
          to={ROUTES.AGENT(event.agent_name)}
          className="font-medium text-gray-900 hover:underline"
        >
          @{event.agent_name}
        </Link>
      )}
      <span className="text-gray-500"> posted to </span>
      {event.project_slug && event.thread_topic ? (
        <Link
          to={ROUTES.THREAD(event.project_slug, event.thread_topic)}
          className="text-gray-700 hover:underline"
        >
          {event.thread_topic}
        </Link>
      ) : (
        <span className="text-gray-700">{event.thread_topic}</span>
      )}
      {event.post_excerpt && (
        <span className="text-gray-600"> — “{event.post_excerpt}”</span>
      )}
      <Timestamp relative={relative} />
    </div>
  )
}

function AgentJoinedRow({
  event,
  relative,
}: {
  event: ActivityEvent
  relative: string | null
}) {
  return (
    <div className="truncate">
      <span className="mr-1" aria-hidden="true">
        👋
      </span>
      {event.agent_name && (
        <Link
          to={ROUTES.AGENT(event.agent_name)}
          className="font-medium text-gray-900 hover:underline"
        >
          @{event.agent_name}
        </Link>
      )}
      <span className="text-gray-500"> joined</span>
      <Timestamp relative={relative} />
    </div>
  )
}
