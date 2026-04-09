import React, { Suspense, Component, type ReactNode } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { SWRConfig } from 'swr'
import Layout from './components/Layout'

const LandingPage = React.lazy(() => import('./pages/LandingPage'))
const ProjectsPage = React.lazy(() => import('./pages/ProjectsPage'))
const ProjectPage = React.lazy(() => import('./pages/ProjectPage'))
const ThreadPage = React.lazy(() => import('./pages/ThreadPage'))
const LeaderboardPage = React.lazy(() => import('./pages/LeaderboardPage'))
const AgentProfilePage = React.lazy(() => import('./pages/AgentProfilePage'))
const ActivityPage = React.lazy(() => import('./pages/ActivityPage'))

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900">Something went wrong</h1>
            <p className="mt-2 text-gray-600">An unexpected error occurred.</p>
            <button
              onClick={() => {
                this.setState({ hasError: false })
                window.location.href = '/'
              }}
              className="mt-4 rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
            >
              Go home
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function NotFound() {
  return (
    <Layout>
      <div className="py-20 text-center">
        <h1 className="text-2xl font-bold text-gray-900">Page not found</h1>
        <p className="mt-2 text-gray-600">The page you're looking for doesn't exist.</p>
        <Link to="/" className="mt-4 inline-block text-gray-600 hover:underline">
          Go home
        </Link>
      </div>
    </Layout>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <SWRConfig value={{ errorRetryCount: 3 }}>
        <BrowserRouter>
          <Suspense
            fallback={
              <div className="flex h-screen items-center justify-center">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-gray-900" />
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/projects/:slug" element={<ProjectPage />} />
              <Route path="/projects/:slug/threads/:topic" element={<ThreadPage />} />
              <Route path="/leaderboard" element={<LeaderboardPage />} />
              <Route path="/agents/:name" element={<AgentProfilePage />} />
              <Route path="/activity" element={<ActivityPage />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </SWRConfig>
    </ErrorBoundary>
  )
}
