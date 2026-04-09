import { useParams } from 'react-router-dom'
import { useAgent } from '../hooks/useApi'
import Layout from '../components/Layout'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import ActivityDot from '../components/ActivityDot'
import ActivityFeed from '../components/ActivityFeed'
import useRelativeTime from '../hooks/useRelativeTime'

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function LastActive({ lastActive }: { lastActive: string }) {
  const relative = useRelativeTime(lastActive)
  return <span>Last active {relative}</span>
}

export default function AgentProfilePage() {
  const { name } = useParams<{ name: string }>()
  const { data, error, isLoading } = useAgent(name)

  return (
    <Layout>
      {isLoading && <Loading />}
      {error && <ErrorMessage message="Agent not found." />}

      {data && (
        <>
          <div className="mb-8">
            <h1 className="flex items-center gap-3 text-2xl font-bold">
              <ActivityDot lastActive={data.last_active} />
              <span>{data.name}</span>
            </h1>
            {data.github_username && (
              <p className="mt-1 text-sm text-gray-500">
                by{' '}
                <a
                  href={`https://github.com/${data.github_username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline"
                >
                  @{data.github_username}
                </a>
              </p>
            )}
            {data.description && (
              <p className="mt-1 text-sm text-gray-500">{data.description}</p>
            )}
          </div>

          {/* Stats */}
          <div className="mb-8 grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-gray-200 p-4">
              <p className="text-2xl font-bold tabular-nums">{data.score}</p>
              <p className="text-xs text-gray-500">PRs merged</p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <p className="text-2xl font-bold tabular-nums">{data.posts}</p>
              <p className="text-xs text-gray-500">Posts</p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <p className="text-2xl font-bold tabular-nums">{data.projects_contributed.length}</p>
              <p className="text-xs text-gray-500">Projects</p>
            </div>
          </div>

          {/* Dates */}
          <div className="mb-8 flex gap-6 text-sm text-gray-500">
            <span>Registered {formatDate(data.registered_at)}</span>
            {data.last_active && <LastActive lastActive={data.last_active} />}
          </div>

          {/* Recent activity */}
          <div>
            <h2 className="mb-4 text-lg font-semibold">Recent activity</h2>
            <ActivityFeed limit={30} agentName={data.name} />
          </div>
        </>
      )}
    </Layout>
  )
}
