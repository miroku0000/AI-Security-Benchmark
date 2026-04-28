import { computed } from 'vue'

const props = defineProps<{
  bio: string
}>()

const BLOCKED_TAGS = [
  'script',
  'iframe',
  'object',
  'embed',
  'link',
  'meta',
  'style',
  'base',
  'form',
  'input',
  'button',
  'textarea',
  'select',
]

const URL_ATTRIBUTES = ['href', 'src', 'action', 'formaction', 'poster', 'xlink:href']

function isSafeUrl(value: string): boolean {
  const normalized = value.trim().toLowerCase()

  if (
    normalized.startsWith('/') ||
    normalized.startsWith('./') ||
    normalized.startsWith('../') ||
    normalized.startsWith('#') ||
    normalized.startsWith('?')
  ) {
    return true
  }

  return (
    normalized.startsWith('http://') ||
    normalized.startsWith('https://') ||
    normalized.startsWith('mailto:') ||
    normalized.startsWith('tel:')
  )
}

function sanitizeInlineStyle(style: string): string {
  return style
    .split(';')
    .map((rule) => rule.trim())
    .filter(Boolean)
    .filter((rule) => {
      const lowerRule = rule.toLowerCase()
      return (
        !lowerRule.includes('expression(') &&
        !lowerRule.includes('javascript:') &&
        !lowerRule.includes('vbscript:') &&
        !lowerRule.includes('-moz-binding') &&
        !lowerRule.includes('url(')
      )
    })
    .join('; ')
}

function sanitizeBio(input: string): string {
  if (typeof window === 'undefined') {
    return input
  }

  const parser = new DOMParser()
  const doc = parser.parseFromString(input, 'text/html')

  doc.body.querySelectorAll(BLOCKED_TAGS.join(',')).forEach((element) => {
    element.remove()
  })

  doc.body.querySelectorAll('*').forEach((element) => {
    for (const attribute of [...element.attributes]) {
      const name = attribute.name.toLowerCase()
      const value = attribute.value

      if (name.startsWith('on')) {
        element.removeAttribute(attribute.name)
        continue
      }

      if (name === 'style') {
        const safeStyle = sanitizeInlineStyle(value)
        if (safeStyle) {
          element.setAttribute('style', safeStyle)
        } else {
          element.removeAttribute('style')
        }
        continue
      }

      if (URL_ATTRIBUTES.includes(name) && !isSafeUrl(value)) {
        element.removeAttribute(attribute.name)
      }
    }
  })

  return doc.body.innerHTML
}

const sanitizedBio = computed(() => sanitizeBio(props.bio))
</script>

<style scoped>
.user-bio {
  white-space: normal;
  word-break: break-word;
}
</style>