import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'

type ImageLightboxProps = {
  open: boolean
  src: string
  alt?: string
  onClose: () => void
}

export function ImageLightbox({ open, src, alt, onClose }: ImageLightboxProps) {
  const dialogLabelId = useId()
  const closeRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    if (!open) return

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      e.preventDefault()
      e.stopImmediatePropagation()
      onClose()
    }

    document.addEventListener('keydown', onKeyDown, true)
    closeRef.current?.focus()

    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown, true)
    }
  }, [open, onClose])

  if (!open || !src.trim()) return null

  const node = (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      data-image-lightbox-open
      role="dialog"
      aria-modal="true"
      aria-labelledby={dialogLabelId}
    >
      <h2 id={dialogLabelId} className="sr-only">
        Xem ảnh phóng to
      </h2>
      <button
        type="button"
        className="absolute inset-0 bg-black/72 backdrop-blur-[2px]"
        aria-label="Đóng xem ảnh"
        onClick={onClose}
      />
      <div className="relative z-[1] flex max-h-[min(92vh,56rem)] max-w-[min(96vw,56rem)] flex-col gap-3">
        <div className="flex items-center justify-end gap-2">
          <a
            href={src}
            target="_blank"
            rel="noreferrer"
            className="u-focus inline-flex items-center gap-1.5 rounded-full bg-white/12 px-3 py-1.5 text-[12px] font-medium text-white backdrop-blur-sm hover:bg-white/20"
          >
            <span
              className="material-symbols-outlined text-[16px]"
              style={{ fontVariationSettings: "'FILL' 0" }}
            >
              open_in_new
            </span>
            Mở tab mới
          </a>
          <button
            ref={closeRef}
            type="button"
            className="u-focus inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/12 text-white backdrop-blur-sm hover:bg-white/20"
            aria-label="Đóng"
            onClick={onClose}
          >
            <span className="material-symbols-outlined text-[22px]">close</span>
          </button>
        </div>
        <div className="overflow-auto rounded-xl bg-black/40 p-2 shadow-2xl ring-1 ring-white/10">
          <img
            src={src}
            alt={alt ?? 'Hình ảnh từ câu trả lời'}
            className="mx-auto max-h-[85vh] w-auto max-w-full object-contain"
          />
        </div>
      </div>
    </div>
  )

  return createPortal(node, document.body)
}
