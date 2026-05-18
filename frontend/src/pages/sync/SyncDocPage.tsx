import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { AuthUser } from '../../types/api'
import type { OcrMethod, SyncJob } from '../../types/sync'
import { clearAuthTokens, getAccessToken } from '../../services/authStorage'
import { getMe } from '../../services/authApi'
import { uploadDocuments } from '../../services/syncApi'

const THEME_STORAGE_KEY = 'career_guidance_theme'
const ALLOWED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']

function createJobId(): string {
  return `job_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    completed: 'u-badge u-badge-success',
    failed: 'u-badge u-badge-error',
    processing: 'u-badge u-badge-info',
  }
  const cls = colorMap[status] ?? 'u-badge'

  return <span className={cls}>{status}</span>
}

export function SyncDocPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    return stored === 'dark' ? 'dark' : 'light'
  })
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null)

  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [ocrMethod, setOcrMethod] = useState<OcrMethod>('gemini')
  const [industryType, setIndustryType] = useState('')
  const [isDragging, setIsDragging] = useState(false)

  const [jobs, setJobs] = useState<SyncJob[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  }, [theme])

  useEffect(() => {
    let isMounted = true
    async function verify() {
      const token = getAccessToken()
      if (!token) { navigate('/login', { replace: true }); return }
      try {
        const user = await getMe()
        if (!isMounted) return
        if (user.role !== 'admin') { navigate('/chat', { replace: true }); return }
        setCurrentUser(user)
      } catch {
        clearAuthTokens()
        navigate('/login', { replace: true })
      } finally {
        if (isMounted) setIsCheckingAuth(false)
      }
    }
    verify()
    return () => { isMounted = false }
  }, [navigate])

  const handleToggleTheme = () => setTheme((p) => (p === 'light' ? 'dark' : 'light'))

  const handleLogout = () => { clearAuthTokens(); navigate('/login', { replace: true }) }

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const valid = Array.from(incoming).filter((f) => {
      const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase()
      return ALLOWED_EXTENSIONS.includes(ext)
    })
    if (valid.length === 0) return
    setSelectedFiles((prev) => {
      const existing = new Set(prev.map((f) => `${f.name}_${f.size}`))
      const deduped = valid.filter((f) => !existing.has(`${f.name}_${f.size}`))
      return [...prev, ...deduped]
    })
  }, [])

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
    },
    [addFiles],
  )

  const handleUpload = async () => {
    if (selectedFiles.length === 0 || isUploading) return
    setErrorMessage('')
    setIsUploading(true)

    const jobId = createJobId()
    const newJob: SyncJob = {
      id: jobId,
      ocrMethod,
      fileNames: selectedFiles.map((f) => f.name),
      industryType: industryType.trim(),
      response: null,
      error: null,
      isUploading: true,
    }
    setJobs((prev) => [newJob, ...prev])

    try {
      const response = await uploadDocuments(
        selectedFiles,
        ocrMethod,
        industryType || undefined,
      )
      setJobs((prev) =>
        prev.map((j) =>
          j.id === jobId
            ? { ...j, response, error: null, isUploading: false }
            : j,
        ),
      )
      setSelectedFiles([])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      setErrorMessage(message)
      setJobs((prev) =>
        prev.map((j) =>
          j.id === jobId
            ? { ...j, error: message, isUploading: false }
            : j,
        ),
      )
    } finally {
      setIsUploading(false)
    }
  }

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
    <div className="h-screen w-full overflow-hidden bg-background text-on-surface kv-texture-overlay">
      <div className="absolute inset-0 z-0" />

      <nav className="fixed left-0 top-0 z-50 flex h-full w-72 flex-col overflow-y-auto bg-surface/98 shadow-[4px_0_48px_rgb(0_0_0_/0.12)] backdrop-blur-xl dark:shadow-[6px_0_56px_rgb(0_0_0_/0.45)]">
        <div className="px-4 pb-4 pt-5">
          <h1 className="font-headline text-[15px] font-bold tracking-tight text-on-surface">
            RecomMind Bot
          </h1>
          <p className="mt-0.5 text-xs text-on-surface/50">Document sync</p>
        </div>

        <div className="px-3 pb-4">
          <button
            className="chat-new-button u-focus w-full rounded-xl py-2.5 px-3 font-headline text-sm font-semibold text-white transition active:scale-[0.99]"
            onClick={() => navigate('/chat')}
            type="button"
          >
            <span className="inline-flex items-center justify-center gap-2">
              <span className="material-symbols-outlined text-[18px]">arrow_back</span>
              Back to chat
            </span>
          </button>
        </div>

        <div className="flex-1 px-3 pb-3">
          <p className="px-1 pb-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface/40">
            Admin
          </p>
          <div className="flex items-center gap-2.5 rounded-xl border border-outline-variant/12 bg-surface-container-high px-3 py-2.5">
            <span className="material-symbols-outlined text-[18px] text-primary/85">
              cloud_upload
            </span>
            <span className="text-sm font-medium text-on-surface/85">Sync documents</span>
          </div>
        </div>

        <div className="mt-auto border-t border-outline-variant/10 px-3 pb-4 pt-3">
          <div className="mb-2 flex gap-2">
            <button
              className="u-focus flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-outline-variant/10 bg-surface-container-high px-2 py-2 text-[11px] font-semibold text-on-surface/65 transition hover:bg-surface-container"
              onClick={handleToggleTheme}
              type="button"
            >
              <span className="material-symbols-outlined text-[16px]">
                {theme === 'dark' ? 'light_mode' : 'dark_mode'}
              </span>
              Theme
            </button>
            <button
              className="u-focus flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-outline-variant/10 bg-surface-container-high px-2 py-2 text-[11px] font-semibold text-on-surface/65 transition hover:bg-surface-container"
              onClick={handleLogout}
              type="button"
            >
              <span className="material-symbols-outlined text-[16px]">logout</span>
              Log out
            </button>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-outline-variant/10 bg-surface-container-high/80 px-3 py-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">
              {(currentUser?.user_name ?? 'A')[0].toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-on-surface">
                {currentUser?.user_name ?? 'Admin'}
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-on-surface/45">
                {currentUser?.role ?? 'admin'}
              </p>
            </div>
          </div>
        </div>
      </nav>

      <main className="relative z-10 ml-72 flex h-full flex-col bg-gradient-to-b from-surface to-background">
        <header className="sticky top-0 z-20 flex flex-shrink-0 items-center border-b border-outline-variant/10 bg-surface/80 px-6 py-3 backdrop-blur-md">
          <div className="flex flex-col gap-0.5">
            <h2 className="font-headline text-base font-semibold tracking-tight text-on-surface">
              Sync documents
            </h2>
            <p className="text-[11px] text-on-surface/45">
              Upload PDFs or images for OCR and indexing
            </p>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-5 pb-10 pt-6 sm:px-8">
          <div className="mx-auto flex max-w-3xl flex-col gap-6">
            <div className="u-card rounded-2xl p-6 sm:p-8">
              <h3 className="font-headline mb-5 text-base font-semibold text-on-surface">
                Upload files
              </h3>

              {/* Drop zone */}
              <div
                className={[
                  'relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 transition-colors cursor-pointer',
                  isDragging
                    ? 'border-primary bg-primary/5'
                    : 'border-outline-variant/25 hover:border-primary/50 hover:bg-surface-container',
                ].join(' ')}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  multiple
                  accept={ALLOWED_EXTENSIONS.join(',')}
                  onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = '' }}
                />
                <span className="material-symbols-outlined text-[40px] text-primary/60 mb-3">
                  cloud_upload
                </span>
                <p className="text-sm font-semibold text-on-surface/80">
                  Drag & drop files here or <span className="text-primary">browse</span>
                </p>
                <p className="mt-1 text-xs text-on-surface/50">
                  PDF, PNG, JPG, TIFF, BMP
                </p>
              </div>

              {/* Selected files */}
              {selectedFiles.length > 0 && (
                <div className="mt-5 flex flex-col gap-2">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-on-surface/60 mb-1">
                    Selected files ({selectedFiles.length})
                  </p>
                  {selectedFiles.map((file, idx) => (
                    <div
                      key={`${file.name}_${file.size}`}
                      className="flex items-center gap-3 rounded-xl bg-surface-container px-4 py-2.5 border border-outline-variant/10"
                    >
                      <span className="material-symbols-outlined text-[18px] text-primary/70">description</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-on-surface truncate">{file.name}</p>
                        <p className="text-[11px] text-on-surface/50">{(file.size / 1024).toFixed(1)} KB</p>
                      </div>
                      <button
                        className="rounded-md p-1 text-on-surface/40 transition hover:text-red-400 hover:bg-red-500/10"
                        onClick={(e) => { e.stopPropagation(); removeFile(idx) }}
                        type="button"
                      >
                        <span className="material-symbols-outlined text-[18px]">close</span>
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* OCR method + industry type */}
              <div className="mt-6 grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2 text-sm font-semibold text-on-surface/80">
                  <p>OCR Method</p>
                  <div className="flex gap-2">
                    {(['gemini', 'paddle'] as OcrMethod[]).map((method) => (
                      <button
                        key={method}
                        aria-pressed={ocrMethod === method}
                        className={[
                          'u-focus relative flex-1 overflow-hidden rounded-xl border px-3 py-2.5 text-xs font-semibold uppercase tracking-wide transition',
                          ocrMethod === method
                            ? 'border-primary/35 bg-primary/10 text-primary'
                            : 'border-outline-variant/15 bg-surface-container text-on-surface/55 hover:border-outline-variant/30 hover:text-on-surface/80',
                        ].join(' ')}
                        onClick={() => setOcrMethod(method)}
                        type="button"
                      >
                        <span className="relative z-10 inline-flex items-center justify-center gap-2">
                          {ocrMethod === method && (
                            <span className="material-symbols-outlined text-[16px]">check_circle</span>
                          )}
                          {method === 'gemini' ? 'Gemini OCR' : 'Paddle OCR'}
                        </span>
                        {ocrMethod === method && (
                          <span className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-primary/15 to-transparent" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
                <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface/80">
                  Industry Type
                  <input
                    className="rounded-xl border border-outline-variant/20 bg-surface px-4 py-2.5 text-sm text-on-surface outline-none transition focus:border-primary"
                    placeholder="e.g. healthcare, finance..."
                    value={industryType}
                    onChange={(e) => setIndustryType(e.target.value)}
                  />
                </label>
              </div>

              {/* Error */}
              {errorMessage && (
                <div className="u-alert u-alert-error mt-4 px-4 py-3 text-sm">
                  {errorMessage}
                </div>
              )}

              {/* Upload button */}
              <button
                className="auth-submit-button mt-6 w-full rounded-2xl px-5 py-3 font-headline text-sm font-bold text-white transition active:scale-[0.98] disabled:cursor-not-allowed"
                disabled={selectedFiles.length === 0 || isUploading}
                onClick={handleUpload}
                type="button"
              >
                {isUploading ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
                    Uploading & Processing...
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2">
                    <span className="material-symbols-outlined text-[18px]">cloud_upload</span>
                    Upload & Process ({selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''})
                  </span>
                )}
              </button>
            </div>

            {/* Job history */}
            {jobs.length > 0 && (
              <div className="u-card rounded-2xl p-6 sm:p-8">
                <h3 className="font-headline mb-5 text-base font-semibold text-on-surface">
                  Processing history
                </h3>
                <div className="flex flex-col gap-4">
                  {jobs.map((job) => (
                    <div
                      key={job.id}
                      className="rounded-2xl border border-outline-variant/10 bg-surface-container px-5 py-4"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <span className="material-symbols-outlined text-[20px] text-primary/70">
                            {job.isUploading ? 'hourglass_top' : job.error ? 'error' : 'check_circle'}
                          </span>
                          <span className="text-xs font-bold uppercase tracking-wider text-on-surface/60">
                            {job.ocrMethod === 'gemini' ? 'Gemini OCR' : 'Paddle OCR'}
                          </span>
                        </div>
                        {job.isUploading ? (
                          <StatusBadge status="processing" />
                        ) : job.error ? (
                          <StatusBadge status="failed" />
                        ) : (
                          <StatusBadge status={job.response?.status ?? 'completed'} />
                        )}
                      </div>

                      <div className="mb-2 flex flex-wrap items-center gap-1.5 text-[11px] text-on-surface/60">
                        {job.fileNames.map((name) => (
                          <span
                            key={name}
                            className="rounded-full border border-outline-variant/15 bg-surface-container-high px-2 py-0.5"
                          >
                            {name}
                          </span>
                        ))}
                        {job.industryType && (
                          <span className="rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-primary">
                            {job.industryType}
                          </span>
                        )}
                      </div>

                      {job.error && (
                        <p className="text-xs text-error">{job.error}</p>
                      )}

                      {job.response && (
                        <div className="grid grid-cols-2 gap-3 mt-3 sm:grid-cols-6">
                          {[
                            { label: 'Downloaded', value: job.response.downloaded },
                            { label: 'Processed', value: job.response.processed },
                            { label: 'Skipped', value: job.response.skipped },
                            { label: 'Failed', value: job.response.failed },
                            { label: 'Pages', value: job.response.total_pages },
                            { label: 'Time', value: formatMs(job.response.execution_time_ms) },
                          ].map((stat) => (
                            <div key={stat.label} className="rounded-xl bg-surface-container-low px-3 py-2 text-center">
                              <p className="text-lg font-headline font-bold text-on-surface">{stat.value}</p>
                              <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface/50">{stat.label}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
