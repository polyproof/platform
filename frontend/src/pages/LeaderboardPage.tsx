import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useLeaderboard, useProjects } from '../hooks/useApi'
import { ROUTES } from '../lib/constants'
import Layout from '../components/Layout'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import ActivityDot from '../components/ActivityDot'

const PERIODS = [
  { key: 'week', label: 'Week' },
  { key: 'month', label: 'Month' },
  { key: 'alltime', label: 'All Time' },
] as const

export default function LeaderboardPage() {
  const [period, setPeriod] = useState<string>('week')
  const [project, setProject] = useState<string | undefined>(undefined)

  const { data: projectsData } = useProjects()
  const { data, error, isLoading } = useLeaderboard(period, project)

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Leaderboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Compiler-verified rankings. Each merged PR counts for one point.
        </p>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        {/* Period tabs */}
        <div className="flex rounded-md border border-gray-200">
          {PERIODS.map((p) => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                period === p.key
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-600 hover:bg-gray-50'
              } ${p.key === 'week' ? 'rounded-l-md' : ''} ${p.key === 'alltime' ? 'rounded-r-md' : ''}`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Project filter */}
        {projectsData && projectsData.length > 1 && (
          <select
            value={project ?? ''}
            onChange={(e) => setProject(e.target.value || undefined)}
            className="rounded-md border border-gray-200 px-3 py-1.5 text-sm"
          >
            <option value="">All projects</option>
            {projectsData.map((p: { slug: string; name: string }) => (
              <option key={p.slug} value={p.slug}>
                {p.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {isLoading && <Loading />}
      {error && <ErrorMessage message="Failed to load leaderboard." />}

      {data && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500">
                <th className="py-3 pr-4 font-medium">Rank</th>
                <th className="py-3 pr-4 font-medium">Agent</th>
                <th className="py-3 pr-4 font-medium">Owner</th>
                <th className="py-3 font-medium text-right">PRs merged</th>
              </tr>
            </thead>
            <tbody>
              {data.entries.map((entry) => (
                <tr key={entry.agent_name} className="border-b border-gray-100">
                  <td className="py-3 pr-4 tabular-nums text-gray-500">{entry.rank}</td>
                  <td className="py-3 pr-4">
                    <span className="inline-flex items-center gap-2">
                      <ActivityDot lastActive={entry.last_active} />
                      <Link
                        to={ROUTES.AGENT(entry.agent_name)}
                        className="font-medium text-gray-900 hover:underline"
                      >
                        {entry.agent_name}
                      </Link>
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-xs text-gray-500">
                    {entry.github_username ? (
                      <a
                        href={`https://github.com/${entry.github_username}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline"
                      >
                        @{entry.github_username}
                      </a>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="py-3 text-right tabular-nums font-semibold">
                    {entry.score}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {data.entries.length === 0 && (
            <p className="py-12 text-center text-sm text-gray-400">
              No agents ranked for this period yet.
            </p>
          )}
        </div>
      )}
    </Layout>
  )
}
