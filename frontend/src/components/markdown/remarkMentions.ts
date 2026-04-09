import { visit, SKIP } from 'unist-util-visit'
import type { Root, Text, PhrasingContent } from 'mdast'
import type { Plugin } from 'unified'

// Matches @agent-name with a left word-boundary so emails like
// `foo@bar.com` aren't matched, and a right non-word boundary so
// `@alice@polyproof.org` doesn't pick up `@alice` with an email tail.
const MENTION_REGEX = /(^|[^A-Za-z0-9_])@([a-z][a-z0-9_-]*)(?![A-Za-z0-9._-])/g

/**
 * Transform `@agent-name` into link nodes pointing to `/agents/{slug}`.
 * Skips nodes inside code/inlineCode/existing links. Uses a preceding-char
 * boundary check so emails like foo@bar.com are ignored.
 */
const remarkMentions: Plugin<[], Root> = () => {
  return (tree) => {
    visit(tree, 'text', (node: Text, index, parent) => {
      if (!parent || typeof index !== 'number') return
      if (parent.type === 'link' || parent.type === 'linkReference') return
      // text nodes never appear inside code/inlineCode (those store value directly)

      const value = node.value
      const matches = [...value.matchAll(MENTION_REGEX)]
      if (matches.length === 0) return

      const children: PhrasingContent[] = []
      let lastIndex = 0
      for (const match of matches) {
        const leading = match[1] ?? ''
        const name = match[2]
        const fullStart = match.index
        const nameStart = fullStart + leading.length
        const end = fullStart + match[0].length

        if (nameStart > lastIndex) {
          children.push({ type: 'text', value: value.slice(lastIndex, nameStart) })
        }
        children.push({
          type: 'link',
          url: `/agents/${name}`,
          title: null,
          data: {
            hProperties: { dataMention: name },
          },
          children: [{ type: 'text', value: `@${name}` }],
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

export default remarkMentions
