import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import { resolveApiMediaUrl } from '../../utils/mediaUrl'
export type AnswerSection = {
  intent_title: string
  query: string
  answer: string
  sources?: Array<Record<string, unknown>>
}

export function SectionedAnswer({
  sections,
  onImageClick,
}: {
  sections: AnswerSection[]
  onImageClick?: (src: string, alt?: string) => void
}) {
  return (
    <div className="flex flex-col gap-4">
      {sections.map((section, index) => (
        <div
          key={`${section.intent_title}-${index}`}
          className="rounded-2xl bg-surface-container-high/75 px-4 py-3 shadow-sm"
        >
          <h3 className="text-[15px] font-semibold text-primary/95">
            {index + 1}. {section.intent_title}
          </h3>
          <p className="mt-1 text-[12px] text-on-surface/55">
            <span className="font-medium text-on-surface/70">Câu hỏi:</span> {section.query}
          </p>
          <div className="mt-2 text-[15px] leading-[1.75] text-on-surface/88">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeSanitize]}
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                ul: ({ children }) => (
                  <ul className="mb-2 list-disc space-y-1 pl-5 marker:text-primary/70">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="mb-2 list-decimal space-y-1 pl-5 marker:text-on-surface/55">{children}</ol>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-primary underline decoration-primary/30 underline-offset-2"
                  >
                    {children}
                  </a>
                ),
                ...(onImageClick
                  ? {
                      img: ({ src, alt }: { src?: string; alt?: string }) => {
                        const raw = src ?? ''
                        if (!raw.trim()) return null
                        const resolved = resolveApiMediaUrl(raw)
                        return (
                          <button
                            type="button"
                            className="u-focus group relative my-2 block w-full max-w-full overflow-hidden rounded-xl bg-surface-container-high/90 p-0 text-left ring-1 ring-on-surface/6 transition hover:ring-primary/30"
                            onClick={() => onImageClick(resolved, alt ?? undefined)}
                            aria-haspopup="dialog"
                            aria-label="Phóng to ảnh"
                          >
                            <img
                              src={resolved}
                              alt={alt ?? ''}
                              className="max-h-64 w-full cursor-zoom-in object-cover transition group-hover:opacity-95"
                              loading="lazy"
                            />
                          </button>
                        )
                      },
                    }
                  : {}),
              }}
            >
              {section.answer}
            </ReactMarkdown>
          </div>
        </div>
      ))}
    </div>
  )
}
