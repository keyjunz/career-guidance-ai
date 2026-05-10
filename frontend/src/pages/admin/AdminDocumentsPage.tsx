import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { AuthUser } from '../../types/api'
import type { AdminDocument } from '../../services/adminApi'
import { clearAuthTokens, getAccessToken } from '../../services/authStorage'
import { getMe } from '../../services/authApi'
import { deleteDocument, fetchDocuments } from '../../services/adminApi'
import { API_BASE_URL } from '../../services/apiClient'

const THEME_STORAGE_KEY = 'career_guidance_theme'
const PAGE_SIZE = 20

function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    completed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
    failed: 'bg-red-500/15 text-red-400 border-red-500/25',
    processing: 'bg-sky-500/15 text-sky-400 border-sky-500/25',
    start: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
  }
  const cls =
    colorMap[status] ??
    'bg-outline-variant/15 text-on-surface/70 border-outline-variant/25'

  return (
    <span
      className={`inline-block rounded-full border px-3 py-0.5 text-[11px] font-bold uppercase tracking-wider ${cls}`}
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
            className="group overflow-hidden rounded-lg border border-outline-variant/20 bg-surface-container-low transition-all hover:border-primary/30 hover:shadow-md"
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
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
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
            className="absolute right-6 top-6 rounded-full bg-white/10 p-2 text-white transition-colors hover:bg-white/20"
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
  isDeleting,
}: {
  doc: AdminDocument
  onDelete: (id: string) => void
  isDeleting: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <div className="rounded-2xl border border-outline-variant/15 bg-surface-container-high/60 backdrop-blur-xl transition-all hover:border-outline-variant/25">
      <div className="flex items-center gap-4 px-5 py-4">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <span className="material-symbols-outlined text-[22px]">
            {doc.document_type === 'pdf' ? 'picture_as_pdf' : 'description'}
          </span>
        </div>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-on-surface">
            {doc.document_name}
          </p>
          <div className="mt-1 flex items-center gap-3 text-[11px] text-on-surface/50">
            <span>{doc.document_type.toUpperCase()}</span>
            <span>·</span>
            <span>{new Date(doc.created_at).toLocaleDateString()}</span>
            {doc.image_urls.length > 0 && (
              <>
                <span>·</span>
                <span>{doc.image_urls.length} images</span>
              </>
            )}
          </div>
        </div>

        <StatusBadge status={doc.status} />

        <button
          type="button"
          className="rounded-lg p-2 text-on-surface/40 transition-colors hover:bg-surface-container-highest hover:text-on-surface/70"
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
            className="rounded-lg p-2 text-on-surface/40 transition-colors hover:bg-red-500/10 hover:text-red-400"
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
              className="rounded-lg bg-red-500/15 px-3 py-1.5 text-[11px] font-bold text-red-400 transition-colors hover:bg-red-500/25"
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
              className="rounded-lg px-2 py-1.5 text-[11px] font-semibold text-on-surface/50 transition-colors hover:bg-surface-container-highest"
              onClick={() => setConfirmDelete(false)}
              disabled={isDeleting}
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {expanded && (
        <div className="border-t border-outline-variant/10 px-5 py-4">
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
    try {
      await deleteDocument(docId)
      setDocuments((prev) => prev.filter((d) => d.id !== docId))
      setTotal((prev) => Math.max(0, prev - 1))
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
      <div className="grid h-screen place-items-center bg-surface text-on-surface">
        <div className="rounded-3xl border border-outline-variant/15 bg-surface-container-high/80 px-8 py-6 text-sm font-semibold text-primary shadow-[0_30px_100px_rgba(0,0,0,0.45)]">
          Verifying admin access...
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface text-on-surface">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-outline-variant/10 bg-surface/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-4">
          <button
            type="button"
            className="rounded-xl p-2 text-on-surface/60 transition-colors hover:bg-surface-container-high hover:text-on-surface"
            onClick={() => navigate('/chat')}
          >
            <span className="material-symbols-outlined text-[22px]">
              arrow_back
            </span>
          </button>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <span
                className="material-symbols-outlined text-[20px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                folder_open
              </span>
            </div>
            <div>
              <h1 className="text-base font-bold">Synced Documents</h1>
              <p className="text-[11px] text-on-surface/50">
                {total} document{total !== 1 ? 's' : ''} total
              </p>
            </div>
          </div>
          <div className="ml-auto text-xs text-on-surface/40">
            {currentUser?.user_name}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-6xl px-6 py-8">
        {error && (
          <div className="mb-6 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {isLoading && documents.length === 0 ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3 text-sm text-on-surface/50">
              <span className="material-symbols-outlined animate-spin text-[20px]">
                progress_activity
              </span>
              Loading documents...
            </div>
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-on-surface/40">
            <span className="material-symbols-outlined mb-3 text-[48px]">
              folder_off
            </span>
            <p className="text-sm font-semibold">No documents found</p>
            <p className="mt-1 text-xs">
              Documents will appear here after syncing.
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
                  isDeleting={deletingId === doc.id}
                />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-2">
                <button
                  type="button"
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-on-surface/60 transition-colors hover:bg-surface-container-high disabled:opacity-30"
                  disabled={currentPage <= 1}
                  onClick={() =>
                    setOffset(Math.max(0, offset - PAGE_SIZE))
                  }
                >
                  Previous
                </button>
                <span className="px-3 text-xs text-on-surface/50">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  type="button"
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-on-surface/60 transition-colors hover:bg-surface-container-high disabled:opacity-30"
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
    </div>
  )
}
