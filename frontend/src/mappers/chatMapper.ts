import type { ApiChatPayload } from '../types/api'
import type { ChatMessage } from '../types/chat'
import { resolveApiMediaUrl } from '../utils/mediaUrl'

export function collectResolvedImageUrls(payload: ApiChatPayload): string[] {
  const seen = new Set<string>()
  const imageUrls: string[] = []
  for (const item of payload.content) {
    if (item.type !== 'image' || !item.image_url) continue
    const resolved = resolveApiMediaUrl(item.image_url.trim())
    if (!resolved || seen.has(resolved)) continue
    seen.add(resolved)
    imageUrls.push(resolved)
  }
  return imageUrls
}

export function mapApiPayloadToAssistantMessage(
  payload: ApiChatPayload,
): ChatMessage {
  const text = payload.content
    .filter((item) => item.type === 'text' && item.text)
    .map((item) => item.text?.trim() || '')
    .filter((item) => item.length > 0)
    .join('\n\n')
  const imageUrls = collectResolvedImageUrls(payload)

  return {
    id: `a_${Date.now()}`,
    role: 'assistant',
    authorLabel: 'RecomMind Bot',
    variant: 'standard',
    text: text || 'No text response from server.',
    imageUrls: imageUrls.length > 0 ? imageUrls : undefined,
    meta: {
      traceId: payload.trace_id,
      executionId: payload.execution_id,
      conversationId: payload.conversation_id,
      cached: payload.cached,
      retrieval_cache_hit: payload.retrieval_cache_hit,
      statuses: payload.statuses,
      sources: payload.sources,
      answer_sections: payload.answer_sections ?? undefined,
    },
  }
}

