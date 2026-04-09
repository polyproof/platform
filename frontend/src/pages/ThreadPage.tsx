import { memo, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useThread, useProjects } from '../hooks/useApi'
import { ROUTES } from '../lib/constants'
import type { Project, Post } from '../lib/types'
import Layout from '../components/Layout'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import Markdown from '../components/Markdown'
import useRelativeTime from '../hooks/useRelativeTime'

const BOT_NAME = 'polyproof-bot'

// Memoize Markdown so that 15-second relative-time re-renders in parent
// post components don't re-run the heavy KaTeX/Shiki/remark pipeline.
// Shallow compare on (children: string, repoUrl: string|undefined) is correct.
const MemoMarkdown = memo(Markdown)

// Absolute timestamp for hover tooltips — keeps the exact time one click
// (or hover) away so relative-time labels don't lose information for
// forum-style reading of older posts.
function formatAbsolute(dateStr: string): string {
  return new Date(dateStr).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

type TimelineEntry =
  | { type: 'post'; post: Post }
  | {
      type: 'bot-chip'
      key: string
      prNumbers: string[]
      latestCreatedAt: string
    }

function extractPrNumbers(body: string): string[] {
  return [...body.matchAll(/#(\d+)/g)].map((m) => m[1])
}

function buildTimeline(posts: Post[]): TimelineEntry[] {
  const entries: TimelineEntry[] = []
  let i = 0
  while (i < posts.length) {
    const post = posts[i]
    if (post.agent_name !== BOT_NAME) {
      entries.push({ type: 'post', post })
      i += 1
      continue
    }
    // Start of a bot run. Collect consecutive bot posts.
    const run: Post[] = []
    while (i < posts.length && posts[i].agent_name === BOT_NAME) {
      run.push(posts[i])
      i += 1
    }
    const prNumbers: string[] = []
    const seen = new Set<string>()
    for (const p of run) {
      for (const n of extractPrNumbers(p.body)) {
        if (!seen.has(n)) {
          seen.add(n)
          prNumbers.push(n)
        }
      }
    }
    entries.push({
      type: 'bot-chip',
      key: run[0].id,
      prNumbers,
      latestCreatedAt: run[run.length - 1].created_at,
    })
  }
  return entries
}

function BotChip({
  prNumbers,
  latestCreatedAt,
  repoUrl,
}: {
  prNumbers: string[]
  latestCreatedAt: string
  repoUrl?: string
}) {
  const relativeTime = useRelativeTime(latestCreatedAt)
  const label =
    prNumbers.length === 0
      ? 'merged'
      : prNumbers.length === 1
      ? `PR #${prNumbers[0]} merged`
      : `PRs ${prNumbers.map((n) => `#${n}`).join(', ')} merged`

  return (
    <div className="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-500">
      <span aria-hidden>✓</span>
      <span>
        {repoUrl && prNumbers.length > 0 ? (
          prNumbers.length === 1 ? (
            <>
              <a
                href={`${repoUrl}/pull/${prNumbers[0]}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline underline-offset-2 hover:text-blue-800"
              >
                PR #{prNumbers[0]}
              </a>{' '}
              merged
            </>
          ) : (
            <>
              PRs{' '}
              {prNumbers.map((n, idx) => (
                <span key={n}>
                  <a
                    href={`${repoUrl}/pull/${n}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 underline underline-offset-2 hover:text-blue-800"
                  >
                    #{n}
                  </a>
                  {idx < prNumbers.length - 1 ? ', ' : ''}
                </span>
              ))}{' '}
              merged
            </>
          )
        ) : (
          label
        )}
      </span>
      <span className="text-gray-400">·</span>
      <span className="text-gray-400" title={formatAbsolute(latestCreatedAt)}>
        {relativeTime}
      </span>
    </div>
  )
}

function PostCard({ post, repoUrl }: { post: Post; repoUrl?: string }) {
  const relativeTime = useRelativeTime(post.created_at)
  return (
    <article className="rounded-lg border border-gray-200 p-5">
      <div className="mb-3 flex items-center gap-3 text-sm">
        <Link
          to={ROUTES.AGENT(post.agent_name)}
          className="font-medium text-gray-900 hover:underline"
        >
          {post.agent_name}
        </Link>
        <span className="text-gray-400" title={formatAbsolute(post.created_at)}>
          {relativeTime}
        </span>
      </div>
      <MemoMarkdown repoUrl={repoUrl}>{post.body}</MemoMarkdown>
    </article>
  )
}

export default function ThreadPage() {
  const { slug, topic } = useParams<{ slug: string; topic: string }>()
  const { data, error, isLoading } = useThread(slug, topic)
  const { data: projectsData } = useProjects()

  const project = projectsData?.find((p: Project) => p.slug === slug)
  const repoUrl = project?.fork_repo
    ? `https://github.com/${project.fork_repo}`
    : undefined

  const timeline = useMemo<TimelineEntry[]>(
    () => (data ? buildTimeline(data.posts) : []),
    [data],
  )

  return (
    <Layout>
      <div className="mb-6">
        <Link to={ROUTES.PROJECT(slug!)} className="text-sm text-gray-500 hover:text-gray-900">
          &larr; Back to {slug}
        </Link>
      </div>

      <h1 className="mb-8 text-2xl font-bold">{topic}</h1>

      {isLoading && <Loading />}
      {error && <ErrorMessage message="Failed to load thread." />}

      {data && (
        <div className="space-y-6">
          {timeline.map((entry) => {
            if (entry.type === 'bot-chip') {
              return (
                <div key={entry.key}>
                  <BotChip
                    prNumbers={entry.prNumbers}
                    latestCreatedAt={entry.latestCreatedAt}
                    repoUrl={repoUrl}
                  />
                </div>
              )
            }
            const { post } = entry
            return <PostCard key={post.id} post={post} repoUrl={repoUrl} />
          })}

          {data.posts.length === 0 && (
            <p className="py-12 text-center text-sm text-gray-400">No posts in this thread yet.</p>
          )}
        </div>
      )}
    </Layout>
  )
}
