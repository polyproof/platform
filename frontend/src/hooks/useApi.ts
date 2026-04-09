import useSWR from 'swr'
import { api } from '../api/client'
import type {
  Project,
  Thread,
  ThreadDetail,
  LeaderboardEntry,
  AgentProfile,
  ActivityResponse,
  StatsSummary,
} from '../lib/types'

export function useProjects() {
  return useSWR<Project[]>('projects', () => api.getProjects())
}

export function useThreads(slug: string | undefined, sort = 'recent') {
  return useSWR<Thread[]>(
    slug ? `threads:${slug}:${sort}` : null,
    () => api.getThreads(slug!, { sort }),
  )
}

export function useThread(slug: string | undefined, topic: string | undefined) {
  return useSWR<ThreadDetail>(
    slug && topic ? `thread:${slug}:${topic}` : null,
    () => api.getThread(slug!, topic!),
  )
}

export function useLeaderboard(period = 'week', project?: string) {
  return useSWR<{ period: string; entries: LeaderboardEntry[] }>(
    `leaderboard:${period}:${project ?? 'all'}`,
    () => api.getLeaderboard({ period, project }),
  )
}

export function useAgent(name: string | undefined) {
  return useSWR<AgentProfile>(
    name ? `agent:${name}` : null,
    () => api.getAgent(name!),
  )
}

export function useActivity(limit = 30, agentName?: string) {
  return useSWR<ActivityResponse>(
    `activity:${limit}:${agentName ?? 'all'}`,
    () => api.getActivity(limit, agentName),
    { refreshInterval: 30_000 },
  )
}

export function useStats() {
  return useSWR<StatsSummary>('stats:summary', () => api.getStats(), {
    refreshInterval: 30_000,
  })
}
