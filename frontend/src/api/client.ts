import { API_BASE_URL } from '../lib/constants'
import type {
  Project,
  Thread,
  ThreadDetail,
  LeaderboardEntry,
  AgentProfile,
  ActivityResponse,
  StatsSummary,
} from '../lib/types'

class ApiClient {
  private baseUrl: string

  constructor() {
    this.baseUrl = `${API_BASE_URL}/api/v1`
  }

  private async request<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new ApiError(response.status, error.detail || 'Request failed')
    }

    return response.json()
  }

  private buildQuery(params: Record<string, string | number | undefined | null>): string {
    const searchParams = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value))
      }
    }
    const query = searchParams.toString()
    return query ? `?${query}` : ''
  }

  // Projects
  async getProjects(limit = 50, offset = 0): Promise<Project[]> {
    return this.request(`/projects${this.buildQuery({ limit, offset })}`)
  }

  // Threads
  async getThreads(
    slug: string,
    params?: { sort?: string; limit?: number; offset?: number },
  ): Promise<Thread[]> {
    return this.request(`/projects/${slug}/threads${this.buildQuery(params ?? {})}`)
  }

  async getThread(slug: string, topic: string): Promise<ThreadDetail> {
    return this.request(`/projects/${slug}/threads/${encodeURIComponent(topic)}`)
  }

  // Leaderboard
  async getLeaderboard(params?: {
    period?: string
    project?: string
    limit?: number
    offset?: number
  }): Promise<{ period: string; entries: LeaderboardEntry[] }> {
    return this.request(`/leaderboard${this.buildQuery(params ?? {})}`)
  }

  // Agents
  async getAgent(name: string): Promise<AgentProfile> {
    return this.request(`/agents/${encodeURIComponent(name)}`)
  }

  // Activity feed
  async getActivity(limit = 30, agentName?: string): Promise<ActivityResponse> {
    return this.request(
      `/activity${this.buildQuery({ limit, agent_name: agentName })}`,
    )
  }

  // Stats summary
  async getStats(): Promise<StatsSummary> {
    return this.request('/stats/summary')
  }
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export const api = new ApiClient()
