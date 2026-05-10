import { API_BASE_URL, apiRequest } from './apiClient'
import { getAccessToken } from './authStorage'

export type AdminDocument = {
  id: string
  user_id: string
  document_name: string
  document_type: string
  ingestion_job_id: string | null
  status: string
  created_at: string
  updated_at: string
  image_urls: string[]
  file_available: boolean
}

export type DocumentListResponse = {
  documents: AdminDocument[]
  total: number
}

export type DocumentDeleteResult = {
  document_deleted: boolean
  vector_deleted: boolean
  file_deleted: boolean
  images_deleted: boolean
  warnings: string[]
}

export async function fetchDocuments(
  limit = 50,
  offset = 0,
): Promise<DocumentListResponse> {
  return apiRequest<DocumentListResponse>(
    `/api/admin/documents?limit=${limit}&offset=${offset}`,
  )
}

export async function fetchDocument(documentId: string): Promise<AdminDocument> {
  return apiRequest<AdminDocument>(`/api/admin/documents/${documentId}`)
}

export async function deleteDocument(
  documentId: string,
): Promise<DocumentDeleteResult> {
  return apiRequest<DocumentDeleteResult>(
    `/api/admin/documents/${documentId}`,
    { method: 'DELETE' },
  )
}

export async function fetchDocumentFileBlob(documentId: string): Promise<Blob> {
  const headers = new Headers()
  const token = getAccessToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(
    `${API_BASE_URL}/api/admin/documents/${documentId}/file`,
    { headers },
  )

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || ''
    let message = response.statusText
    try {
      if (contentType.includes('application/json')) {
        const data = (await response.json()) as { detail?: string }
        if (typeof data.detail === 'string') message = data.detail
      } else {
        const text = await response.text()
        if (text) message = text
      }
    } catch {
      /* keep message */
    }
    throw new Error(message || 'Failed to download file')
  }

  return response.blob()
}
