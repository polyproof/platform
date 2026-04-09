import { visit, SKIP } from 'unist-util-visit'
import type { Root, Text, PhrasingContent } from 'mdast'
import type { Plugin } from 'unified'

export interface RemarkPrLinksOptions {
  repoUrl?: string
}

// Matches `PR #123`, `pr#123`, or bare `#123` with a left word-boundary
// (start-of-string or a non-word, non-`#` character) so `##24`, `foo#24`,
// and URL fragments like `http://example.com/#42` don't get rewritten.
// Also requires a right non-word boundary so `#24a` doesn't match `#24`.
const PR_REGEX = /(^|[^A-Za-z0-9#_/])(PR\s*#|#)(\d+)(?![A-Za-z0-9_])/gi

/**
 * Transform `#N` and `PR #N` text sequences into link nodes pointing to
 * `{repoUrl}/pull/{N}`. Skips nodes inside code/inlineCode/existing links.
 * If `repoUrl` is missing/empty, does nothing.
 */
const remarkPrLinks: Plugin<[RemarkPrLinksOptions?], Root> = (options) => {
  const repoUrl = options?.repoUrl?.replace(/\/$/, '')

  return (tree) => {
    if (!repoUrl) return

    visit(tree, 'text', (node: Text, index, parent) => {
      if (!parent || typeof index !== 'number') return
      if (parent.type === 'link' || parent.type === 'linkReference') return
      // text nodes never appear inside code/inlineCode (those store value directly)

      const value = node.value
      const matches = [...value.matchAll(PR_REGEX)]
      if (matches.length === 0) return

      const children: PhrasingContent[] = []
      let lastIndex = 0
      for (const match of matches) {
        const leading = match[1] ?? ''
        const prefix = match[2] // "PR #" or "#"
        const num = match[3]
        const fullStart = match.index
        const linkStart = fullStart + leading.length
        const end = fullStart + match[0].length

        if (linkStart > lastIndex) {
          children.push({ type: 'text', value: value.slice(lastIndex, linkStart) })
        }
        children.push({
          type: 'link',
          url: `${repoUrl}/pull/${num}`,
          title: null,
          data: {
            // Use the hast camelCase form directly so the sanitize schema's
            // `dataPr` allowlist matches without relying on property-info
            // normalization.
            hProperties: { dataPr: num },
          },
          children: [{ type: 'text', value: `${prefix}${num}` }],
        })
        lastIndex = end
      }
      if (lastIndex < value.length) {
        children.push({ type: 'text', value: value.slice(lastIndex) })
      }

      parent.children.splice(index, 1, ...children)
      return [SKIP, index + children.length]
    })
  }
}

export default remarkPrLinks
