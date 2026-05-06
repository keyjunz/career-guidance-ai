export type ApiChatRequest = {
  user_id: string
  message: string
  conversation_id?: string
}

export type ApiChatContentItem = {
  type: 'text' | 'image'
  text?: string | null
  image_url?: string | null
}

export type ApiChatPayload = {
  type: 'text' | 'image' | 'mixed'
  content: ApiChatContentItem[]
  conversation_id: string
  trace_id: string
  statuses: string[]
  cached: boolean
}

export type ApiEnvelope<T> = {
  success?: boolean
  message?: string
  data?: T
  trace_id?: string
}

