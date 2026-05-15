export type ChatMode = 'auto' | 'rag' | 'web'

export type ApiChatRequest = {
  question: string
  plan?: 'rag_only' | 'web_only' | null
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
  execution_id?: string
  trace_id?: string
  statuses?: string[]
  sources?: Array<Record<string, unknown>>
  cached?: boolean
  retrieval_cache_hit?: boolean
  answer_sections?: Array<Record<string, unknown>> | null
}

export type ApiEnvelope<T> = {
  success?: boolean
  message?: string
  data?: T
  trace_id?: string
}

export type AuthUser = {
  id: string
  user_name: string
  email: string
  phone: string | null
  is_active: boolean
  role: string
  created_at: string
  updated_at: string
}

export type LoginRequest = {
  email: string
  password: string
}

export type RegisterRequest = {
  user_name: string
  email: string
  password: string
  phone?: string | null
}

export type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
  user: AuthUser
}

