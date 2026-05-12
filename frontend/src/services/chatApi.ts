import type { ApiChatPayload, ApiChatRequest, ApiEnvelope } from '../types/api'
import { API_BASE_URL, apiRequest } from './apiClient'
import { getAccessToken } from './authStorage'

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
  const json = await apiRequest<ApiEnvelope<ApiChatPayload> | ApiChatPayload>(
    '/api/chat?invocation_type=sync',
    {
      method: 'POST',
      body,
    },
  )

  return extractPayload(json)
}

type StreamHandlers = {
  onToken: (token: string) => void
  onStatus?: (status: string) => void
  onFinalPayload?: (payload: ApiChatPayload) => void
  onDone?: (executionId?: string) => void
}

export type StreamChatOptions = {
  signal?: AbortSignal
}

/** True when fetch/read was aborted (user stop or navigation). */
export function isStreamAbortError(error: unknown): boolean {
  if (error instanceof DOMException && error.name === 'AbortError') return true
  if (error instanceof Error && error.name === 'AbortError') return true
  return false
}

export async function streamChatMessage(
  body: ApiChatRequest,
  handlers: StreamHandlers,
  options?: StreamChatOptions,
): Promise<void> {
  const token = getAccessToken()
  if (!token) {
    throw new Error('Not authenticated')
  }

  const signal = options?.signal

  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok || !response.body) {
    const payload = await response.text()
    throw new Error(payload || 'Failed to initialize chat stream.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const processEvent = (rawEvent: string) => {
    const lines = rawEvent.split('\n')
    let eventName = 'message'
    const dataLines: string[] = []

    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim())
      }
    }

    if (dataLines.length === 0) return
    const dataRaw = dataLines.join('\n')
    let payload: Record<string, unknown> = {}
    try {
      payload = JSON.parse(dataRaw)
    } catch {
      payload = { raw: dataRaw }
    }

    if (eventName === 'token') {
      handlers.onToken(String(payload.token ?? ''))
      return
    }
    if (eventName === 'status') {
      handlers.onStatus?.(String(payload.status ?? ''))
      return
    }
    if (eventName === 'error') {
      throw new Error(
        String(payload.message ?? payload.error ?? 'Failed to process chat stream.'),
      )
    }
    if (eventName === 'done') {
      handlers.onDone?.(
        payload.execution_id ? String(payload.execution_id) : undefined,
      )
      return
    }
    if (eventName === 'final_payload') {
      try {
        handlers.onFinalPayload?.(extractPayload(payload as ApiChatPayload))
      } catch {
        // ignore malformed final payload events
      }
    }
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      let eventBoundary = buffer.indexOf('\n\n')
      while (eventBoundary >= 0) {
        const rawEvent = buffer.slice(0, eventBoundary).trim()
        buffer = buffer.slice(eventBoundary + 2)
        if (rawEvent) {
          processEvent(rawEvent)
        }
        eventBoundary = buffer.indexOf('\n\n')
      }
    }
  } catch (err) {
    await reader.cancel().catch(() => {})
    if (isStreamAbortError(err)) {
      throw err
    }
    throw err
  }
}

