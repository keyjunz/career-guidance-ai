export type SyncDocResponse = {
  job_id: string
  status: string
  processed: number
  failed: number
  downloaded: number
  skipped: number
  total_pages: number
  file_page_counts: Record<string, number>
  execution_time_ms: number
}

export type OcrMethod = 'paddle' | 'gemini'

export type SyncJob = {
  id: string
  ocrMethod: OcrMethod
  fileNames: string[]
  industryType: string
  response: SyncDocResponse | null
  error: string | null
  isUploading: boolean
}
