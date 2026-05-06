import type { ApiChatPayload, ApiChatRequest, ApiEnvelope } from '../types/api'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || 'http://localhost:8000'

function buildUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

function extractPayload(
  json: ApiEnvelope<ApiChatPayload> | ApiChatPayload,
): ApiChatPayload {
  if ('conversation_id' in json && 'content' in json) {
    return json
  }

  if (json.data && 'conversation_id' in json.data) {
    return json.data
  }

  throw new Error('Invalid chat response payload.')
}

export async function sendChatMessage(
  body: ApiChatRequest,
): Promise<ApiChatPayload> {
  const response = await fetch(buildUrl('/api/chat?invocation_type=sync'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  const json = (await response.json()) as ApiEnvelope<ApiChatPayload> | ApiChatPayload

  if (!response.ok) {
    const reason =
      (json as ApiEnvelope<ApiChatPayload>).message || 'Failed to send message.'
    throw new Error(reason)
  }

  return extractPayload(json)
}

