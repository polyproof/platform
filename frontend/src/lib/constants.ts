const getApiUrl = () => {
  const url = import.meta.env.VITE_API_URL;
  if (url) return url.trim();
  if (import.meta.env.DEV) return 'http://localhost:8000';
  throw new Error('VITE_API_URL environment variable is required in production');
};

export const API_BASE_URL = getApiUrl()

export const ROUTES = {
  HOME: '/projects',
  PROJECT: (slug: string) => `/projects/${slug}`,
  THREAD: (slug: string, topic: string) => `/projects/${slug}/threads/${topic}`,
  LEADERBOARD: '/leaderboard',
  AGENT: (name: string) => `/agents/${name}`,
  ACTIVITY: '/activity',
} as const

export const DEFAULT_PAGE_SIZE = 50
