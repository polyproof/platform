import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import rehypeSanitize from 'rehype-sanitize'
import rehypeShikiFromHighlighter from '@shikijs/rehype/core'
import { createHighlighterCoreSync } from '@shikijs/core'
import { createJavaScriptRegexEngine } from 'shiki/engine/javascript'
import lean4 from '@shikijs/langs/lean4'
import python from '@shikijs/langs/python'
import bash from '@shikijs/langs/bash'
import diff from '@shikijs/langs/diff'
import json from '@shikijs/langs/json'
import githubLight from '@shikijs/themes/github-light'

import remarkPrLinks from './markdown/remarkPrLinks'
import remarkMentions from './markdown/remarkMentions'
import sanitizeSchema from './markdown/sanitizeSchema'

// Build the highlighter once at module load. Sync + JS regex engine keeps
// bundling simple and avoids the WASM fetch. Preloaded languages only.
const highlighter = createHighlighterCoreSync({
  themes: [githubLight],
  langs: [lean4, python, bash, diff, json],
  engine: createJavaScriptRegexEngine(),
})

interface MarkdownProps {
  children: string
  repoUrl?: string
}

export default function Markdown({ children, repoUrl }: MarkdownProps) {
  const { remarkPlugins, rehypePlugins } = useMemo(() => {
    return {
      remarkPlugins: [
        remarkGfm,
        remarkMath,
        [remarkPrLinks, { repoUrl }],
        remarkMentions,
      ] as const,
      rehypePlugins: [
        rehypeKatex,
        [
          rehypeShikiFromHighlighter,
          highlighter,
          {
            theme: 'github-light',
            fallbackLanguage: 'text',
          },
        ],
        // Sanitize must always run last so KaTeX + Shiki output survives
        // plugin transforms but any malicious HTML gets stripped.
        [rehypeSanitize, sanitizeSchema],
      ] as const,
    }
  }, [repoUrl])

  return (
    <div className="prose prose-sm max-w-none prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-200 prose-code:text-sm [&_a]:text-blue-600 [&_a]:underline [&_a]:underline-offset-2 hover:[&_a]:text-blue-800">
      <ReactMarkdown
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        remarkPlugins={remarkPlugins as any}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        rehypePlugins={rehypePlugins as any}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
