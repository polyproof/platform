import { defaultSchema } from 'hast-util-sanitize'
import type { Schema } from 'hast-util-sanitize'

const MATHML_TAGS = [
  'math',
  'semantics',
  'annotation',
  'mrow',
  'mi',
  'mo',
  'mn',
  'ms',
  'mtext',
  'mspace',
  'msup',
  'msub',
  'msubsup',
  'mfrac',
  'msqrt',
  'mroot',
  'mtable',
  'mtr',
  'mtd',
  'mstyle',
  'mover',
  'munder',
  'munderover',
]

const baseAttributes = defaultSchema.attributes ?? {}
const baseTagNames = defaultSchema.tagNames ?? []

/**
 * Extended sanitize schema that keeps KaTeX MathML output and Shiki's
 * inline styles intact, plus lets our custom remark plugins tag anchors
 * with data attributes for future styling.
 */
export const sanitizeSchema: Schema = {
  ...defaultSchema,
  tagNames: [...baseTagNames, ...MATHML_TAGS],
  attributes: {
    ...baseAttributes,
    span: [...(baseAttributes.span ?? []), 'className', 'style', 'ariaHidden'],
    div: [...(baseAttributes.div ?? []), 'className', 'style'],
    code: [...(baseAttributes.code ?? []), 'className', 'style'],
    pre: [...(baseAttributes.pre ?? []), 'className', 'style'],
    a: [
      ...(baseAttributes.a ?? []),
      'className',
      'style',
      'target',
      'rel',
      ['dataPr', /^\d+$/],
      'dataMention',
    ],
    annotation: ['encoding'],
    math: ['xmlns', 'display'],
    // Allow the full MathML attribute set KaTeX's output uses. These
    // are enumerated rather than a wildcard so we don't accidentally
    // allow `href` or `onclick` on MathML elements.
    mrow: ['className', 'mathvariant'],
    mi: ['className', 'mathvariant'],
    mo: [
      'className',
      'mathvariant',
      'stretchy',
      'fence',
      'lspace',
      'rspace',
      'symmetric',
      'minsize',
      'maxsize',
      'accent',
      'form',
      'separator',
    ],
    mn: ['className', 'mathvariant'],
    ms: ['className', 'mathvariant'],
    mtext: ['className', 'mathvariant'],
    mspace: ['className', 'width', 'height', 'depth', 'linebreak'],
    msup: ['className'],
    msub: ['className'],
    msubsup: ['className'],
    mfrac: ['className', 'linethickness'],
    msqrt: ['className'],
    mroot: ['className'],
    mtable: ['className', 'columnalign', 'rowalign', 'columnlines', 'rowlines', 'columnspacing', 'rowspacing'],
    mtr: ['className', 'columnalign', 'rowalign'],
    mtd: ['className', 'columnalign', 'rowalign', 'columnspan', 'rowspan'],
    mstyle: [
      'className',
      'mathvariant',
      'mathbackground',
      'mathcolor',
      'scriptlevel',
      'displaystyle',
      'scriptsizemultiplier',
      'scriptminsize',
    ],
    mover: ['className', 'accent'],
    munder: ['className', 'accentunder'],
    munderover: ['className', 'accent', 'accentunder'],
    semantics: ['className'],
  },
}

export default sanitizeSchema
