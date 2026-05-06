import type { OcrMethod, SyncDocResponse } from '../types/sync'
import { API_BASE_URL, ApiError } from './apiClient'
import { getAccessToken } from './authStorage'

const UPLOAD_ENDPOINTS: Record<OcrMethod, string> = {
  paddle: '/api/sync-documents/upload',
  gemini: '/api/sync-documents/upload-gemini',
}

export async function uploadDocuments(
  files: File[],
  ocrMethod: OcrMethod,
  industryType?: string,
): Promise<SyncDocResponse> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  if (industryType?.trim()) {
    formData.append('industry_type', industryType.trim())
  }

  const endpoint = UPLOAD_ENDPOINTS[ocrMethod]
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const message =
      typeof payload === 'object'
        ? payload?.detail || payload?.error || 'Upload failed'
        : String(payload)
    throw new ApiError(message, response.status, payload)
  }

  return payload as SyncDocResponse
}

export async function getSyncStatus(jobId: string): Promise<SyncDocResponse> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const response = await fetch(
    `${API_BASE_URL}/api/sync-documents/status/${encodeURIComponent(jobId)}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  )

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const message =
      typeof payload === 'object'
        ? payload?.detail || payload?.error || 'Status check failed'
        : String(payload)
    throw new ApiError(message, response.status, payload)
  }

  return payload as SyncDocResponse
}
