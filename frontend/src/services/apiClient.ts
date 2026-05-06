import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
} from './authStorage'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || 'http://localhost:8000'

type ApiRequestOptions = {
  method?: string
  body?: unknown
  headers?: HeadersInit
  auth?: boolean
}

type RefreshAccessTokenResponse = {
  access_token: string
  token_type: string
}

export class ApiError extends Error {
  status: number
  payload: unknown

  constructor(message: string, status: number, payload: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

function buildUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

function getErrorMessage(payload: unknown): string {
  if (payload && typeof payload === 'object') {
    const record = payload as Record<string, unknown>
    const detail = record.detail
    const message = record.message
    const error = record.error

    if (typeof detail === 'string') return detail
    if (typeof message === 'string') return message
    if (typeof error === 'string') return error
  }

  return 'Request failed.'
}

let refreshInFlight: Promise<string | null> | null = null

async function requestRefreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null

  const response = await fetch(buildUrl('/api/auth/refresh'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? ((await response.json()) as RefreshAccessTokenResponse)
    : null

  if (!response.ok || !payload?.access_token) {
    clearAuthTokens()
    return null
  }

  setAccessToken(payload.access_token)
  return payload.access_token
}

async function getRefreshedAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = requestRefreshAccessToken().finally(() => {
      refreshInFlight = null
    })
  }

  return refreshInFlight
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const method = options.method ?? 'GET'
  const isFormData = options.body instanceof FormData

  const requestBody: BodyInit | undefined =
    options.body === undefined
      ? undefined
      : isFormData
        ? (options.body as FormData)
        : JSON.stringify(options.body)

  const callApi = async (tokenOverride?: string) => {
    const headers = new Headers(options.headers)

    if (options.body !== undefined && !isFormData && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    if (options.auth !== false) {
      const token = tokenOverride ?? getAccessToken()
      if (token) {
        headers.set('Authorization', `Bearer ${token}`)
      }
    }

    const response = await fetch(buildUrl(path), {
      method,
      headers,
      body: requestBody,
    })

    const contentType = response.headers.get('content-type') || ''
    const payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text()

    return { response, payload }
  }

  const firstAttempt = await callApi()
  if (
    firstAttempt.response.status === 401 &&
    options.auth !== false &&
    path !== '/api/auth/refresh'
  ) {
    const refreshedToken = await getRefreshedAccessToken()
    if (refreshedToken) {
      const retryAttempt = await callApi(refreshedToken)
      if (!retryAttempt.response.ok) {
        throw new ApiError(
          getErrorMessage(retryAttempt.payload),
          retryAttempt.response.status,
          retryAttempt.payload,
        )
      }

      return retryAttempt.payload as T
    }
  }

  if (!firstAttempt.response.ok) {
    throw new ApiError(
      getErrorMessage(firstAttempt.payload),
      firstAttempt.response.status,
      firstAttempt.payload,
    )
  }

  return firstAttempt.payload as T
}
