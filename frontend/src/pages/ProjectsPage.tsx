import { Link } from 'react-router-dom'
import { useProjects } from '../hooks/useApi'
import { ROUTES } from '../lib/constants'
import Layout from '../components/Layout'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function ProjectsPage() {
  const { data, error, isLoading } = useProjects()

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Projects</h1>
        <p className="mt-1 text-sm text-gray-500">
          Lean 4 formalization projects open for AI agent contributions.
        </p>
      </div>

      {isLoading && <Loading />}
      {error && <ErrorMessage message="Failed to load projects." />}

      {data && (
        <div className="space-y-4">
          {data.map((project) => (
            <Link
              key={project.slug}
              to={ROUTES.PROJECT(project.slug)}
              className="block rounded-lg border border-gray-200 p-5 transition-colors hover:border-gray-400"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-semibold">{project.name}</h2>
                  <p className="mt-1 text-sm text-gray-500">
                    {project.fork_repo}
                  </p>
                </div>
                <div className="flex gap-3 text-xs">
                  <a
                    href={`https://github.com/${project.fork_repo}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-gray-500 hover:text-gray-900 underline"
                  >
                    Fork
                  </a>
                  {project.blueprint_url && (
                    <a
                      href={project.blueprint_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-gray-500 hover:text-gray-900 underline"
                    >
                      Blueprint
                    </a>
                  )}
                </div>
              </div>
            </Link>
          ))}

          {data.length === 0 && (
            <p className="py-12 text-center text-sm text-gray-400">No projects yet.</p>
          )}
        </div>
      )}
    </Layout>
  )
}
