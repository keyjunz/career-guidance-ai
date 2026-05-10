import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { AuthUser } from '../../types/api'
import type { AdminDocument } from '../../services/adminApi'
import { clearAuthTokens, getAccessToken } from '../../services/authStorage'
import { getMe } from '../../services/authApi'
import {
  deleteDocument,
  fetchDocumentFileBlob,
  fetchDocuments,
} from '../../services/adminApi'
import { API_BASE_URL } from '../../services/apiClient'

const THEME_STORAGE_KEY = 'career_guidance_theme'
const PAGE_SIZE = 20

function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    completed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
    failed: 'bg-red-500/15 text-red-400 border-red-500/25',
    processing: 'bg-primary/12 text-primary border-primary/25',
    start: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
  }
  const cls =
    colorMap[status] ??
    'bg-outline-variant/15 text-on-surface/70 border-outline-variant/25'

  return (
    <span
      className={`inline-block rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}
    >
      {status}
    </span>
  )
}

function ImageGallery({
  imageUrls,
  documentName,
}: {
  imageUrls: string[]
  documentName: string
}) {
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null)

  if (imageUrls.length === 0) {
    return (
      <p className="py-3 text-center text-xs text-on-surface/40">
        No extracted images
      </p>
    )
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {imageUrls.map((url) => (
          <button
            key={url}
            type="button"
            className="u-focus group overflow-hidden rounded-lg border border-outline-variant/15 bg-surface-container-low transition hover:border-primary/25 hover:shadow-sm"
            onClick={() => setLightboxSrc(`${API_BASE_URL}${url}`)}
          >
            <img
              src={`${API_BASE_URL}${url}`}
              alt={`Extracted from ${documentName}`}
              className="h-28 w-full object-cover transition-transform duration-200 group-hover:scale-105"
              loading="lazy"
            />
          </button>
        ))}
      </div>

      {lightboxSrc && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-md"
          onClick={() => setLightboxSrc(null)}
          onKeyDown={(e) => e.key === 'Escape' && setLightboxSrc(null)}
          role="button"
          tabIndex={0}
        >
          <img
            src={lightboxSrc}
            alt="Full size preview"
            className="max-h-[85vh] max-w-[90vw] rounded-xl shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            type="button"
            className="u-focus absolute right-4 top-4 rounded-full bg-white/12 p-2 text-white transition-colors hover:bg-white/20 sm:right-6 sm:top-6"
            onClick={() => setLightboxSrc(null)}
          >
            <span className="material-symbols-outlined text-[24px]">close</span>
          </button>
        </div>
      )}
    </>
  )
}

function DocumentCard({
  doc,
  onDelete,
  onPreviewPdf,
  onOpenPdf,
  onDownloadPdf,
  isDeleting,
}: {
  doc: AdminDocument
  onDelete: (id: string) => void
  onPreviewPdf: (doc: AdminDocument) => void
  onOpenPdf: (doc: AdminDocument) => void
  onDownloadPdf: (doc: AdminDocument) => void
  isDeleting: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <div className="u-card rounded-2xl transition-colors hover:border-outline-variant/25">
      <div className="flex flex-wrap items-center gap-3 px-4 py-3.5 sm:flex-nowrap sm:gap-4 sm:px-5 sm:py-4">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <span className="material-symbols-outlined text-[22px]">
            {doc.document_type === 'pdf' ? 'picture_as_pdf' : 'description'}
          </span>
        </div>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-on-surface">
            {doc.document_name}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-on-surface/50">
            <span>{doc.document_type.toUpperCase()}</span>
            <span>·</span>
            <span>{new Date(doc.created_at).toLocaleDateString()}</span>
            {doc.image_urls.length > 0 && (
              <>
                <span>·</span>
                <span>{doc.image_urls.length} images</span>
              </>
            )}
            {doc.file_available && (
              <>
                <span className="hidden sm:inline">·</span>
                <span className="flex flex-wrap gap-1">
                  <button
                    type="button"
                    className="u-focus rounded-md bg-primary px-2 py-0.5 text-[11px] font-semibold text-white shadow-sm hover:opacity-95"
                    onClick={() => onPreviewPdf(doc)}
                  >
                    Preview
                  </button>
                  <button
                    type="button"
                    className="u-focus rounded-md border border-outline-variant/20 bg-surface-container-high px-2 py-0.5 text-[11px] font-medium text-on-surface/75 hover:bg-surface-container-highest"
                    onClick={() => onOpenPdf(doc)}
                  >
                    Open
                  </button>
                  <button
                    type="button"
                    className="u-focus rounded-md border border-outline-variant/20 bg-transparent px-2 py-0.5 text-[11px] font-medium text-on-surface/60 hover:bg-surface-container-high"
                    onClick={() => onDownloadPdf(doc)}
                  >
                    Download
                  </button>
                </span>
              </>
            )}
          </div>
        </div>

        <StatusBadge status={doc.status} />

        <button
          type="button"
          className="u-focus rounded-lg p-2 text-on-surface/40 transition-colors hover:bg-surface-container-highest hover:text-on-surface/70"
          onClick={() => setExpanded(!expanded)}
          title={expanded ? 'Collapse' : 'Show images'}
        >
          <span className="material-symbols-outlined text-[20px]">
            {expanded ? 'expand_less' : 'expand_more'}
          </span>
        </button>

        {!confirmDelete ? (
          <button
            type="button"
            className="u-focus rounded-lg p-2 text-on-surface/40 transition-colors hover:bg-red-500/10 hover:text-red-400"
            onClick={() => setConfirmDelete(true)}
            disabled={isDeleting}
            title="Delete document"
          >
            <span className="material-symbols-outlined text-[20px]">delete</span>
          </button>
        ) : (
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="u-focus rounded-lg bg-red-500/15 px-3 py-1.5 text-[11px] font-semibold text-red-300 transition-colors hover:bg-red-500/25"
              onClick={() => {
                onDelete(doc.id)
                setConfirmDelete(false)
              }}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Confirm'}
            </button>
            <button
              type="button"
              className="u-focus rounded-lg px-2 py-1.5 text-[11px] font-medium text-on-surface/50 transition-colors hover:bg-surface-container-highest"
              onClick={() => setConfirmDelete(false)}
              disabled={isDeleting}
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {expanded && (
        <div className="border-t border-outline-variant/10 px-4 py-3.5 sm:px-5 sm:py-4">
          <ImageGallery
            imageUrls={doc.image_urls}
            documentName={doc.document_name}
          />
        </div>
      )}
    </div>
  )
}

export function AdminDocumentsPage() {
  const navigate = useNavigate()
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null)
  const [documents, setDocuments] = useState<AdminDocument[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [deleteNotice, setDeleteNotice] = useState('')
  const [pdfPreview, setPdfPreview] = useState<{
    url: string
    name: string
  } | null>(null)

  useEffect(() => {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    document.documentElement.setAttribute(
      'data-theme',
      stored === 'dark' ? 'dark' : 'light',
    )
  }, [])

  useEffect(() => {
    let mounted = true
    async function verify() {
      const token = getAccessToken()
      if (!token) {
        navigate('/login', { replace: true })
        return
      }
      try {
        const user = await getMe()
        if (!mounted) return
        if (user.role !== 'admin') {
          navigate('/chat', { replace: true })
          return
        }
        setCurrentUser(user)
      } catch {
        clearAuthTokens()
        navigate('/login', { replace: true })
      } finally {
        if (mounted) setIsCheckingAuth(false)
      }
    }
    verify()
    return () => {
      mounted = false
    }
  }, [navigate])

  useEffect(() => {
    return () => {
      if (pdfPreview?.url) {
        URL.revokeObjectURL(pdfPreview.url)
      }
    }
  }, [pdfPreview?.url])

  const openPdfModal = useCallback(async (doc: AdminDocument) => {
    setError('')
    try {
      const blob = await fetchDocumentFileBlob(doc.id)
      const url = URL.createObjectURL(blob)
      setPdfPreview((prev) => {
        if (prev?.url) URL.revokeObjectURL(prev.url)
        return { url, name: doc.document_name }
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load PDF')
    }
  }, [])

  const openPdfInNewTab = useCallback(async (doc: AdminDocument) => {
    setError('')
    try {
      const blob = await fetchDocumentFileBlob(doc.id)
      const url = URL.createObjectURL(blob)
      const w = window.open(url, '_blank', 'noopener,noreferrer')
      if (!w) {
        setError('Popup blocked — allow popups or use Preview.')
        URL.revokeObjectURL(url)
        return
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open PDF')
    }
  }, [])

  const downloadPdf = useCallback(async (doc: AdminDocument) => {
    setError('')
    try {
      const blob = await fetchDocumentFileBlob(doc.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = doc.document_name || 'document.pdf'
      a.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download PDF')
    }
  }, [])

  const loadDocuments = useCallback(async (currentOffset: number) => {
    setIsLoading(true)
    setError('')
    try {
      const res = await fetchDocuments(PAGE_SIZE, currentOffset)
      setDocuments(res.documents)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isCheckingAuth && currentUser) {
      loadDocuments(offset)
    }
  }, [isCheckingAuth, currentUser, offset, loadDocuments])

  const handleDelete = async (docId: string) => {
    setDeletingId(docId)
    setDeleteNotice('')
    try {
      const result = await deleteDocument(docId)
      setDocuments((prev) => prev.filter((d) => d.id !== docId))
      setTotal((prev) => Math.max(0, prev - 1))
      if (result.warnings.length > 0) {
        setDeleteNotice(result.warnings.join(' '))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document')
    } finally {
      setDeletingId(null)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  if (isCheckingAuth) {
    return (
      <div className="grid h-screen place-items-center bg-background text-on-surface">
        <div className="u-card rounded-2xl px-8 py-6 text-sm font-medium text-on-surface/70">
          Verifying admin access...
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background text-on-surface kv-texture-overlay">
      <header className="sticky top-0 z-20 border-b border-outline-variant/10 bg-surface/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3 sm:px-6 sm:py-3.5">
          <button
            type="button"
            className="u-focus rounded-xl p-2 text-on-surface/55 transition-colors hover:bg-surface-container-high hover:text-on-surface"
            onClick={() => navigate('/chat')}
          >
            <span className="material-symbols-outlined text-[22px]">
              arrow_back
            </span>
          </button>
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/12 text-primary">
              <span
                className="material-symbols-outlined text-[20px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                folder_open
              </span>
            </div>
            <div className="min-w-0">
              <h1 className="font-headline truncate text-sm font-semibold sm:text-base">
                Synced documents
              </h1>
              <p className="text-[11px] text-on-surface/45">
                {total} document{total !== 1 ? 's' : ''} total
              </p>
            </div>
          </div>
          <div className="ml-auto hidden truncate text-xs text-on-surface/40 sm:block">
            {currentUser?.user_name}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        {error && (
          <div className="mb-5 rounded-xl border border-red-400/25 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}
        {deleteNotice && (
          <div className="mb-5 rounded-xl border border-amber-400/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-100/90">
            {deleteNotice}
          </div>
        )}

        {isLoading && documents.length === 0 ? (
          <div className="flex items-center justify-center py-16 sm:py-20">
            <div className="u-card flex items-center gap-3 rounded-2xl px-6 py-4 text-sm font-medium text-on-surface/55">
              <span className="material-symbols-outlined animate-spin text-[20px] text-primary/80">
                progress_activity
              </span>
              Loading documents…
            </div>
          </div>
        ) : documents.length === 0 ? (
          <div className="u-card mx-auto flex max-w-md flex-col items-center justify-center rounded-2xl px-6 py-12 text-center text-on-surface/45">
            <span className="material-symbols-outlined mb-3 text-[44px] text-on-surface/30">
              folder_off
            </span>
            <p className="text-sm font-semibold text-on-surface/70">
              No documents yet
            </p>
            <p className="mt-1.5 text-xs leading-relaxed">
              Documents appear here after you sync from the admin upload page.
            </p>
          </div>
        ) : (
          <>
            <div className="space-y-3">
              {documents.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  doc={doc}
                  onDelete={handleDelete}
                  onPreviewPdf={openPdfModal}
                  onOpenPdf={openPdfInNewTab}
                  onDownloadPdf={downloadPdf}
                  isDeleting={deletingId === doc.id}
                />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-2">
                <button
                  type="button"
                  className="u-focus rounded-lg border border-outline-variant/15 bg-surface-container-high/60 px-3 py-1.5 text-xs font-medium text-on-surface/65 transition-colors hover:bg-surface-container-high disabled:opacity-30"
                  disabled={currentPage <= 1}
                  onClick={() =>
                    setOffset(Math.max(0, offset - PAGE_SIZE))
                  }
                >
                  Previous
                </button>
                <span className="px-3 text-xs text-on-surface/45">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  type="button"
                  className="u-focus rounded-lg border border-outline-variant/15 bg-surface-container-high/60 px-3 py-1.5 text-xs font-medium text-on-surface/65 transition-colors hover:bg-surface-container-high disabled:opacity-30"
                  disabled={currentPage >= totalPages}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </main>

      {pdfPreview && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-md"
          role="dialog"
          aria-modal="true"
          aria-label="PDF preview"
        >
          <div className="relative flex h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-outline-variant/15 bg-surface shadow-2xl">
            <div className="flex items-center justify-between border-b border-outline-variant/10 px-4 py-3">
              <p className="truncate pr-4 text-sm font-semibold text-on-surface">
                {pdfPreview.name}
              </p>
              <button
                type="button"
                className="u-focus rounded-lg p-2 text-on-surface/60 hover:bg-surface-container-high"
                onClick={() => {
                  setPdfPreview((prev) => {
                    if (prev?.url) URL.revokeObjectURL(prev.url)
                    return null
                  })
                }}
              >
                <span className="material-symbols-outlined text-[22px]">close</span>
              </button>
            </div>
            <iframe
              title={pdfPreview.name}
              src={pdfPreview.url}
              className="min-h-0 flex-1 w-full bg-surface-container-low"
            />
          </div>
        </div>
      )}
    </div>
  )
}
