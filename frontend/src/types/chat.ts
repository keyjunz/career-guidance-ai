export type ChatRole = 'user' | 'assistant'

export type ChatAction = {
  id: string
  label: string
  icon: string
  align?: 'left' | 'right'
}

export type ChatBentoItem = {
  label: string
  value: string
}

export type ChatMessage = {
  id: string
  role: ChatRole
  authorLabel: string
  text: string
  createdAtLabel?: string
  variant?: 'standard' | 'luminary'
  title?: string
  actions?: ChatAction[]
  bento?: ChatBentoItem[]
  meta?: {
    traceId?: string
    conversationId?: string
    cached?: boolean
    statuses?: string[]
  }
}

