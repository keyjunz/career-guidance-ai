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
    completed:
      'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
    failed:
      'bg-red-500/15 text-red-400 border-red-500/25',
    processing:
      'bg-sky-500/15 text-sky-400 border-sky-500/25',
  }
  const cls = colorMap[status] ?? 'bg-outline-variant/15 text-on-surface/70 border-outline-variant/25'

  return (
    <span className={`inline-block rounded-full border px-3 py-0.5 text-[11px] font-bold uppercase tracking-wider ${cls}`}>
      {status}
    </span>
  )
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
      <div className="grid h-screen place-items-center bg-surface text-on-surface">
        <div className="rounded-3xl border border-outline-variant/15 bg-surface-container-high/80 px-8 py-6 text-sm font-semibold text-primary shadow-[0_30px_100px_rgba(0,0,0,0.45)]">
          Verifying admin access...
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen w-full overflow-hidden bg-surface text-on-surface kv-texture-overlay">
      <div className="absolute inset-0 z-0" />

      {/* Minimal sidebar strip */}
      <nav className="fixed left-0 top-0 z-50 flex h-full w-72 flex-col overflow-y-auto rounded-r-2xl bg-surface-container-low py-8 shadow-[4px_0_40px_rgba(0,0,0,0.18)]">
        <div className="px-8 mb-8">
          <h1 className="font-headline text-lg font-bold tracking-tight text-sky-400 mb-1">
            Kinetic Assistant
          </h1>
          <p className="font-body text-sm text-on-surface/70">Document Sync Portal</p>
        </div>

        <div className="px-6 mb-6">
          <button
            className="chat-new-button w-full rounded-xl py-3 px-4 font-headline text-sm font-bold text-white transition-transform duration-200 active:scale-95"
            onClick={() => navigate('/chat')}
            type="button"
          >
            <span className="inline-flex items-center justify-center gap-2">
              <span className="material-symbols-outlined text-[18px]">arrow_back</span>
              Back to Chat
            </span>
          </button>
        </div>

        <div className="flex-1 px-4 flex flex-col gap-1">
          <p className="px-4 mb-2 text-[10px] font-semibold uppercase tracking-widest text-on-surface/60">
            Admin Tools
          </p>
          <div className="mx-2 flex items-center gap-3 rounded-lg bg-gradient-to-r from-sky-500 to-sky-600 px-3 py-2 text-white shadow-[0_0_15px_rgba(56,189,248,0.30)]">
            <span className="material-symbols-outlined text-[20px]">cloud_upload</span>
            <span className="text-sm font-medium">Sync Documents</span>
          </div>
        </div>

        {/* User info + controls */}
        <div className="px-4 mt-auto pt-6 relative">
          <div className="absolute left-8 right-8 top-0 h-px bg-outline-variant/10" />

          <div className="mx-2 mb-3 flex gap-2">
            <button
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-surface-container-high px-3 py-2 text-xs font-semibold text-on-surface/60 transition hover:bg-surface-container-highest hover:text-on-surface"
              onClick={handleToggleTheme}
              type="button"
            >
              <span className="material-symbols-outlined text-[16px]">
                {theme === 'dark' ? 'light_mode' : 'dark_mode'}
              </span>
              Theme
            </button>
            <button
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-surface-container-high px-3 py-2 text-xs font-semibold text-on-surface/60 transition hover:bg-surface-container-highest hover:text-on-surface"
              onClick={handleLogout}
              type="button"
            >
              <span className="material-symbols-outlined text-[16px]">logout</span>
              Logout
            </button>
          </div>

          <div className="mx-2 flex items-center gap-3 rounded-xl bg-surface-container-high px-4 py-3 border border-outline-variant/10">
            <div className="w-8 h-8 rounded-full bg-primary-container/20 flex items-center justify-center flex-shrink-0 text-primary">
              <span className="font-headline text-xs font-bold">
                {(currentUser?.user_name ?? 'A')[0].toUpperCase()}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-on-surface">{currentUser?.user_name ?? 'Admin'}</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-primary-dim">
                {currentUser?.role ?? 'admin'}
              </span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="ml-72 flex h-full flex-col relative z-10">
        <header className="flex-shrink-0 px-10 py-8 flex items-center justify-between z-20">
          <div className="flex flex-col gap-1">
            <h2 className="font-headline text-2xl font-extrabold tracking-tight text-on-surface">
              Sync Documents
            </h2>
            <div className="flex items-center gap-2">
              <span className="relative h-2 w-2 rounded-full bg-primary shadow-[0_0_10px_rgba(59,191,250,0.80)]">
                <span className="absolute inset-0 rounded-full bg-primary animate-ping opacity-50" />
              </span>
              <span className="text-xs font-semibold uppercase tracking-widest text-primary-dim">
                OCR Processing Engine
              </span>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-10 pb-10">
          <div className="mx-auto max-w-3xl flex flex-col gap-8">
            {/* Upload card */}
            <div className="rounded-3xl border border-outline-variant/15 bg-surface-container-high/80 p-8 shadow-[0_30px_100px_rgba(0,0,0,0.45)] backdrop-blur">
              <h3 className="font-headline text-lg font-bold text-on-surface mb-6">
                Upload Files
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
                <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface/80">
                  OCR Method
                  <div className="flex gap-2">
                    {(['gemini', 'paddle'] as OcrMethod[]).map((method) => (
                      <button
                        key={method}
                        className={[
                          'flex-1 rounded-xl px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition border',
                          ocrMethod === method
                            ? 'bg-primary/15 text-primary border-primary/30'
                            : 'bg-surface-container text-on-surface/60 border-outline-variant/15 hover:border-primary/30',
                        ].join(' ')}
                        onClick={() => setOcrMethod(method)}
                        type="button"
                      >
                        {method === 'gemini' ? 'Gemini OCR' : 'Paddle OCR'}
                      </button>
                    ))}
                  </div>
                </label>
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
                <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
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
              <div className="rounded-3xl border border-outline-variant/15 bg-surface-container-high/80 p-8 shadow-[0_30px_100px_rgba(0,0,0,0.45)] backdrop-blur">
                <h3 className="font-headline text-lg font-bold text-on-surface mb-6">
                  Processing History
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

                      <div className="text-xs text-on-surface/60 mb-2">
                        {job.fileNames.join(', ')}
                        {job.industryType && (
                          <span className="ml-2 text-primary-dim">({job.industryType})</span>
                        )}
                      </div>

                      {job.error && (
                        <p className="text-xs text-red-400">{job.error}</p>
                      )}

                      {job.response && (
                        <div className="grid grid-cols-4 gap-3 mt-3">
                          {[
                            { label: 'Processed', value: job.response.processed },
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
