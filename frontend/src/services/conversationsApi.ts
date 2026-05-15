import { apiRequest } from './apiClient'

export type ApiConversationSummary = {
  id: string
  title: string
  started_at: string | null
  preview: string
}

export type ApiConversationMessage = {
  id: string
  role: 'user' | 'assistant'
  text: string
  timestamp: string | null
}

export async function fetchConversations(
  limit = 50,
  offset = 0,
): Promise<ApiConversationSummary[]> {
  return apiRequest<ApiConversationSummary[]>(
    `/api/chat/conversations?limit=${limit}&offset=${offset}`,
  )
}

export async function fetchConversationMessages(
  conversationId: string,
  page = 1,
  pageSize = 100,
): Promise<ApiConversationMessage[]> {
  return apiRequest<ApiConversationMessage[]>(
    `/api/chat/conversations/${conversationId}/messages?page=${page}&page_size=${pageSize}`,
  )
}

export async function renameConversation(
  conversationId: string,
  title: string,
): Promise<void> {
  await apiRequest<{ ok: boolean }>(`/api/chat/conversations/${conversationId}`, {
    method: 'PATCH',
    body: { title },
  })
}

export async function deleteConversationApi(conversationId: string): Promise<void> {
  await apiRequest<{ ok: boolean }>(`/api/chat/conversations/${conversationId}`, {
    method: 'DELETE',
  })
}
