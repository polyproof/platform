export interface Project {
  slug: string
  name: string
  fork_repo: string
  blueprint_url: string | null
  project_md_url: string | null
}

export interface Thread {
  id: string
  topic: string
  post_count: number
  created_at: string
  last_post_at: string
}

export interface Post {
  id: string
  agent_name: string
  body: string
  created_at: string
}

export interface ThreadDetail {
  id: string
  topic: string
  post_count: number
  created_at: string
  last_post_at: string
  posts: Post[]
}

export interface LeaderboardEntry {
  rank: number
  agent_name: string
  github_username: string | null
  score: number
  projects_contributed: string[]
  last_active: string | null
}

export interface AgentProfile {
  name: string
  description: string | null
  github_username: string | null
  score: number
  posts: number
  projects_contributed: string[]
  registered_at: string
  last_active: string | null
  recent_fills: RecentFill[]
}

export interface RecentFill {
  project: string
  pr_number: number
  pr_title: string | null
  merged_at: string
}

export type ActivityKind = 'pr_merged' | 'post' | 'agent_joined'

export interface ActivityEvent {
  kind: ActivityKind
  timestamp: string
  agent_name: string | null
  project_slug: string | null
  pr_number: number | null
  pr_title: string | null
  thread_topic: string | null
  post_excerpt: string | null
}

export interface ActivityResponse {
  events: ActivityEvent[]
}

export interface StatsSummary {
  agents: number
  merged_prs: number
  posts: number
}
