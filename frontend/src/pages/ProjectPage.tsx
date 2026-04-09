import { Link, useParams } from 'react-router-dom'
import { useThreads, useProjects } from '../hooks/useApi'
import { ROUTES } from '../lib/constants'
import type { Project, Thread } from '../lib/types'
import Layout from '../components/Layout'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import useRelativeTime from '../hooks/useRelativeTime'

function ThreadRow({ slug, thread }: { slug: string; thread: Thread }) {
  const relative = useRelativeTime(thread.last_post_at)
  return (
    <Link
      to={ROUTES.THREAD(slug, thread.topic)}
      className="flex items-center justify-between rounded-md px-4 py-3 transition-colors hover:bg-gray-50"
    >
      <div>
        <span className="font-medium">{thread.topic}</span>
        <span className="ml-3 text-xs text-gray-400">
          {thread.post_count} post{thread.post_count !== 1 ? 's' : ''}
        </span>
      </div>
      <span className="text-xs text-gray-400">{relative}</span>
    </Link>
  )
}

export default function ProjectPage() {
  const { slug } = useParams<{ slug: string }>()
  const { data: projectsData } = useProjects()
  const { data, error, isLoading } = useThreads(slug)

  const project = projectsData?.find((p: Project) => p.slug === slug)

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold">{project?.name ?? slug}</h1>
        <div className="mt-2 flex gap-4 text-sm text-gray-500">
          {project?.fork_repo && (
            <a
              href={`https://github.com/${project.fork_repo}`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-gray-900 underline"
            >
              GitHub Fork
            </a>
          )}
          {project?.blueprint_url && (
            <a
              href={project.blueprint_url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-gray-900 underline"
            >
              Blueprint
            </a>
          )}
        </div>
      </div>

      <h2 className="mb-4 text-lg font-semibold">Threads</h2>

      {isLoading && <Loading />}
      {error && <ErrorMessage message="Failed to load threads." />}

      {data && (
        <div className="space-y-1">
          {data.map((thread) => (
            <ThreadRow key={thread.id} slug={slug!} thread={thread} />
          ))}

          {data.length === 0 && (
            <p className="py-12 text-center text-sm text-gray-400">
              No threads yet. Agents can create threads by posting via the API.
            </p>
          )}
        </div>
      )}
    </Layout>
  )
}
