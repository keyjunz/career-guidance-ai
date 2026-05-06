import type { ApiChatPayload } from '../types/api'
import type { ChatMessage } from '../types/chat'

export function mapApiPayloadToAssistantMessage(
  payload: ApiChatPayload,
): ChatMessage {
  const firstTextItem = payload.content.find(
    (item) => item.type === 'text' && item.text,
  )
  const imageUrls = payload.content
    .filter((item) => item.type === 'image' && item.image_url)
    .map((item) => item.image_url?.trim() || '')
    .filter((url) => url.length > 0)

  return {
    id: `a_${Date.now()}`,
    role: 'assistant',
    authorLabel: 'Kinetic AI',
    variant: 'standard',
    text: firstTextItem?.text?.trim() || 'No text response from server.',
    imageUrls: imageUrls.length > 0 ? imageUrls : undefined,
    meta: {
      traceId: payload.trace_id,
      conversationId: payload.conversation_id,
      cached: payload.cached,
      statuses: payload.statuses,
    },
  }
}

