import type { ApiChatPayload } from '../types/api'
import type { ChatMessage } from '../types/chat'

export function mapApiPayloadToAssistantMessage(
  payload: ApiChatPayload,
): ChatMessage {
  const text = payload.content
    .filter((item) => item.type === 'text' && item.text)
    .map((item) => item.text?.trim() || '')
    .filter((item) => item.length > 0)
    .join('\n\n')
  const imageUrls = payload.content
    .filter((item) => item.type === 'image' && item.image_url)
    .map((item) => item.image_url?.trim() || '')
    .filter((url) => url.length > 0)

  return {
    id: `a_${Date.now()}`,
    role: 'assistant',
    authorLabel: 'Kinetic AI',
    variant: 'standard',
    text: text || 'No text response from server.',
    imageUrls: imageUrls.length > 0 ? imageUrls : undefined,
    meta: {
      traceId: payload.trace_id,
      executionId: payload.execution_id,
      conversationId: payload.conversation_id,
      cached: payload.cached,
      statuses: payload.statuses,
      sources: payload.sources,
    },
  }
}

