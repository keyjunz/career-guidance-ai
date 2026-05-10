import { apiRequest } from './apiClient'

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
}

export type DocumentListResponse = {
  documents: AdminDocument[]
  total: number
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

export async function deleteDocument(documentId: string): Promise<void> {
  await apiRequest(`/api/admin/documents/${documentId}`, { method: 'DELETE' })
}
