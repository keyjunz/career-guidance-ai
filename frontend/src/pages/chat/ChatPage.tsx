import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { SideNav } from '../../components/layout/SideNav'
import { ChatHeader } from '../../components/layout/ChatHeader'
import { ChatThread } from '../../components/chat/ChatThread'
import { ChatInputDock } from '../../components/chat/ChatInputDock'
import type { ChatConversation, ChatMessage } from '../../types/chat'
import type { AuthUser, ChatMode } from '../../types/api'
import {
  isStreamAbortError,
  sendChatMessage,
  streamChatMessage,
} from '../../services/chatApi'
import {
  collectResolvedImageUrls,
  mapApiPayloadToAssistantMessage,
} from '../../mappers/chatMapper'
import { resolveApiMediaUrl } from '../../utils/mediaUrl'
import { clearAuthTokens, getAccessToken } from '../../services/authStorage'
import { getMe } from '../../services/authApi'
import {
  deleteConversationApi,
  fetchConversationMessages,
  fetchConversations,
  renameConversation,
  type ApiConversationMessage,
} from '../../services/conversationsApi'

const BOT_LABEL = 'RecomMind Bot'
const THEME_STORAGE_KEY = 'career_guidance_theme'

function createId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value,
  )
}

function createEmptyConversation(): ChatConversation {
  return {
    id: crypto.randomUUID(),
    title: 'New conversation',
    createdAt: new Date().toISOString(),
    messages: [],
  }
}

function mapApiMessagesToChat(
  rows: ApiConversationMessage[],
  userName: string,
): ChatMessage[] {
  return rows.map((row) => ({
    id: row.id,
    role: row.role,
    authorLabel: row.role === 'user' ? userName : BOT_LABEL,
    text: row.text,
    imageUrls:
      row.image_urls && row.image_urls.length > 0
        ? row.image_urls.map((url) => resolveApiMediaUrl(url))
        : undefined,
  }))
}

function firstNameFromUserName(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return ''
  return trimmed.split(/\s+/)[0] ?? ''
}

/* -------------------------------------------------------------------------- */

export function ChatPage() {
  const navigate = useNavigate()
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    return stored === 'dark' ? 'dark' : 'light'
  })
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null)
  const [chatMode, setChatMode] = useState<ChatMode>('auto')
  const [conversations, setConversations] = useState<ChatConversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string>('')
  const [apiTypingConversationId, setApiTypingConversationId] = useState<
    string | null
  >(null)

  const activeConversation = useMemo(
    () =>
      conversations.find(
        (conversation) => conversation.id === activeConversationId,
      ),
    [conversations, activeConversationId],
  )
  const activeMessages = useMemo(
    () => activeConversation?.messages ?? [],
    [activeConversation],
  )
  const dayChip = useMemo(
    () =>
      activeMessages.find((message) => message.createdAtLabel)?.createdAtLabel ??
      'Today',
    [activeMessages],
  )

  /* ---- derived helpers ---- */
  const isTyping = activeConversationId === apiTypingConversationId
  const streamAbortRef = useRef<AbortController | null>(null)

  /* ---- stop handler ---- */
  const handleStopStream = () => {
    streamAbortRef.current?.abort()
  }

  /* ---- keyboard Escape to stop ---- */
  useEffect(() => {
    if (!isTyping) return

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      e.preventDefault()
      streamAbortRef.current?.abort()
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isTyping])

  /* ---- theme ---- */
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  }, [theme])

  /* ---- session verify + conversations load ---- */
  useEffect(() => {
    let isMounted = true

    async function verifySession() {
      const token = getAccessToken()
      if (!token) {
        navigate('/login', { replace: true })
        return
      }

      try {
        const user = await getMe()
        if (isMounted) {
          setCurrentUser(user)
          try {
            const list = await fetchConversations()
            if (list.length === 0) {
              const initialConversation = createEmptyConversation()
              setConversations([initialConversation])
              setActiveConversationId(initialConversation.id)
            } else {
              const mapped: ChatConversation[] = list.map((item) => ({
                id: item.id,
                title: item.title,
                createdAt: item.started_at ?? new Date().toISOString(),
                messages: [],
                conversationIdFromApi: item.id,
              }))
              setConversations(mapped)
              const firstId = mapped[0].id
              setActiveConversationId(firstId)
              const rows = await fetchConversationMessages(firstId)
              setConversations((prev) =>
                prev.map((conversation) =>
                  conversation.id === firstId
                    ? {
                        ...conversation,
                        messages: mapApiMessagesToChat(rows, user.user_name),
                      }
                    : conversation,
                ),
              )
            }
          } catch {
            const initialConversation = createEmptyConversation()
            setConversations([initialConversation])
            setActiveConversationId(initialConversation.id)
          }
        }
      } catch {
        clearAuthTokens()
        navigate('/login', { replace: true })
      } finally {
        if (isMounted) {
          setIsCheckingAuth(false)
        }
      }
    }

    verifySession()

    return () => {
      isMounted = false
    }
  }, [navigate])

  /* ---- new chat ---- */
  const handleNewChat = () => {
    const nextConversation = createEmptyConversation()
    setConversations((prev) => [nextConversation, ...prev])
    setActiveConversationId(nextConversation.id)
    setErrorMessage('')
  }

  /* ---- load history ---- */
  const loadMessagesForConversation = async (conversationId: string) => {
    if (!currentUser || !isUuid(conversationId)) return
    try {
      const rows = await fetchConversationMessages(conversationId)
      setConversations((prev) =>
        prev.map((conversation) =>
          conversation.id === conversationId
            ? {
                ...conversation,
                messages: mapApiMessagesToChat(rows, currentUser.user_name),
              }
            : conversation,
        ),
      )
    } catch {
      setErrorMessage('Không thể tải lịch sử cuộc trò chuyện.')
    }
  }

  /* ---- select conversation ---- */
  const handleSelectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId)
    setErrorMessage('')
    const selected = conversations.find((c) => c.id === conversationId)
    if (selected && selected.messages.length === 0 && isUuid(conversationId)) {
      void loadMessagesForConversation(conversationId)
    }
  }

  /* ---- rename ---- */
  const handleRenameConversation = (conversationId: string, nextTitle: string) => {
    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, title: nextTitle }
          : conversation,
      ),
    )
    if (isUuid(conversationId)) {
      void renameConversation(conversationId, nextTitle).catch((err) => {
        setErrorMessage(
          err instanceof Error ? err.message : 'Failed to rename conversation.',
        )
      })
    }
  }

  /* ---- delete ---- */
  const handleDeleteConversation = (conversationId: string) => {
    const remainingConversations = conversations.filter(
      (conversation) => conversation.id !== conversationId,
    )
    const fallbackConversation =
      remainingConversations[0] ?? createEmptyConversation()
    const nextConversations =
      remainingConversations.length > 0
        ? remainingConversations
        : [fallbackConversation]

    setConversations(nextConversations)
    setActiveConversationId(fallbackConversation.id)

    if (apiTypingConversationId === conversationId) {
      setApiTypingConversationId(null)
    }
    setErrorMessage('')

    if (isUuid(conversationId)) {
      void deleteConversationApi(conversationId).catch((err) => {
        setErrorMessage(
          err instanceof Error ? err.message : 'Failed to delete conversation.',
        )
      })
    }
  }

  /* ---- logout ---- */
  const handleLogout = () => {
    clearAuthTokens()
    navigate('/login', { replace: true })
  }

  /* ---- theme toggle ---- */
  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'))
  }

  /* ---- send message ---- */
  const handleSend = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isTyping || !activeConversationId) return

    setErrorMessage('')
    setApiTypingConversationId(activeConversationId)

    const optimisticUserMessage: ChatMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      authorLabel: currentUser?.user_name ?? 'You',
      text: trimmed,
    }
    const streamingAssistantId = createId('a_stream')
    const streamingAssistantMessage: ChatMessage = {
      id: streamingAssistantId,
      role: 'assistant',
      authorLabel: BOT_LABEL,
      text: '',
    }

    // Thêm tin nhắn người dùng + assistant trống vào UI
    setConversations((prev) =>
      prev.map((conversation) => {
        if (conversation.id !== activeConversationId) return conversation
        const currentTitle =
          conversation.title === 'New conversation' ? trimmed : conversation.title
        return {
          ...conversation,
          title: currentTitle,
          messages: [
            ...conversation.messages,
            optimisticUserMessage,
            streamingAssistantMessage,
          ],
        }
      }),
    )

    const planValue =
      chatMode === 'rag'
        ? ('rag_only' as const)
        : chatMode === 'web'
          ? ('web_only' as const)
          : undefined

    const conversationIdForApi = isUuid(activeConversationId)
      ? activeConversationId
      : undefined

    const streamController = new AbortController()
    streamAbortRef.current = streamController

    let streamedText = ''
    let latestStatus = ''

    try {
      /* --- inner try: stream the response --- */
      try {
        let streamedExecutionId: string | undefined
        let streamedConversationId: string | undefined
        let streamedImageUrls: string[] | undefined
        let streamedSources: Array<Record<string, unknown>> | undefined
        let streamedStatuses: string[] | undefined
        let streamedCached: boolean | undefined
        let streamedRetrievalCacheHit: boolean | undefined
        let streamedAnswerSections: Array<Record<string, unknown>> | undefined

        await streamChatMessage(
          {
            question: trimmed,
            ...(planValue ? { plan: planValue } : {}),
            ...(conversationIdForApi
              ? { conversation_id: conversationIdForApi }
              : {}),
          },
          {
            onToken: (token) => {
              streamedText += token
              setConversations((prev) =>
                prev.map((conversation) =>
                  conversation.id === activeConversationId
                    ? {
                        ...conversation,
                        messages: conversation.messages.map((message) =>
                          message.id === streamingAssistantId
                            ? { ...message, text: streamedText || ' ' }
                            : message,
                        ),
                      }
                    : conversation,
                ),
              )
            },
            onStatus: (status) => {
              latestStatus = status
              if (streamedText.trim()) return
              const statusText = `Processing: ${status}`
              setConversations((prev) =>
                prev.map((conversation) =>
                  conversation.id === activeConversationId
                    ? {
                        ...conversation,
                        messages: conversation.messages.map((message) =>
                          message.id === streamingAssistantId
                            ? { ...message, text: statusText }
                            : message,
                        ),
                      }
                    : conversation,
                ),
              )
            },
            onDone: (executionId) => {
              streamedExecutionId = executionId
            },
            onFinalPayload: (payload) => {
              streamedConversationId = payload.conversation_id
              streamedStatuses = payload.statuses
              streamedCached = payload.cached
              streamedRetrievalCacheHit = payload.retrieval_cache_hit
              streamedAnswerSections = payload.answer_sections ?? undefined
              streamedSources = payload.sources
              const images = collectResolvedImageUrls(payload)
              if (images.length > 0) {
                streamedImageUrls = images
              }
            },
          },
          { signal: streamController.signal },
        )

        // Stream hoàn tất → cập nhật final message
        setConversations((prev) =>
          prev.map((conversation) =>
            conversation.id === activeConversationId
              ? {
                  ...conversation,
                  conversationIdFromApi:
                    streamedConversationId ?? conversation.conversationIdFromApi,
                  messages: conversation.messages.map((message) =>
                    message.id === streamingAssistantId
                      ? {
                          ...message,
                          text:
                            message.text.trim() ||
                            (latestStatus
                              ? `Processing: ${latestStatus}`
                              : 'No text response from server.'),
                          meta: {
                            executionId: streamedExecutionId,
                            conversationId: streamedConversationId,
                            statuses: streamedStatuses,
                            cached: streamedCached,
                            retrieval_cache_hit: streamedRetrievalCacheHit,
                            answer_sections: streamedAnswerSections,
                            sources: streamedSources,
                          },
                          imageUrls: streamedImageUrls,
                        }
                      : message,
                  ),
                }
              : conversation,
          ),
        )
        return
      } catch (streamErr) {
        if (isStreamAbortError(streamErr)) {
          // Người dùng dừng → giữ lại text đã stream, đánh dấu stopped
          const stoppedSuffix = '\n\n*(Đã dừng.)*'
          const base =
            streamedText.trim() ||
            (latestStatus.trim()
              ? `Processing: ${latestStatus}`
              : '')
          const finalStoppedText = base
            ? `${base}${stoppedSuffix}`
            : stoppedSuffix.trim()

          setConversations((prev) =>
            prev.map((conversation) =>
              conversation.id === activeConversationId
                ? {
                    ...conversation,
                    messages: conversation.messages.map((message) =>
                      message.id === streamingAssistantId
                        ? {
                            ...message,
                            text: finalStoppedText,
                            meta: {
                              ...message.meta,
                              stopped: true,
                            },
                          }
                        : message,
                    ),
                  }
                : conversation,
            ),
          )
          return
        }
        // Lỗi khác (ko phải abort) → bỏ tin nhắn tạm, fallback sang sync
        setConversations((prev) =>
          prev.map((conversation) =>
            conversation.id === activeConversationId
              ? {
                  ...conversation,
                  messages: conversation.messages.filter(
                    (message) => message.id !== streamingAssistantId,
                  ),
                }
              : conversation,
          ),
        )
      }

      /* --- sync fallback --- */
      const payload = await sendChatMessage({
        question: trimmed,
        ...(planValue ? { plan: planValue } : {}),
        ...(conversationIdForApi
          ? { conversation_id: conversationIdForApi }
          : {}),
      })
      const assistantMessage = mapApiPayloadToAssistantMessage(payload)
      setConversations((prev) =>
        prev.map((conversation) =>
          conversation.id === activeConversationId
            ? {
                ...conversation,
                conversationIdFromApi: payload.conversation_id,
                messages: [...conversation.messages, assistantMessage],
              }
            : conversation,
        ),
      )
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to connect chat API.'
      setErrorMessage(message)
    } finally {
      streamAbortRef.current = null
      setApiTypingConversationId((prev) =>
        prev === activeConversationId ? null : prev,
      )
    }
  }

  /* ---- render ---- */
  if (isCheckingAuth) {
    return (
      <div className="grid h-screen place-items-center bg-background text-on-surface">
        <div className="u-card rounded-2xl px-8 py-6 text-sm font-medium text-on-surface/70">
          Verifying secure session…
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell-bg h-screen w-full overflow-hidden text-on-surface kv-texture-overlay">
      <div className="absolute inset-0 z-0" />
      <SideNav
        conversations={conversations}
        activeConversationId={activeConversationId}
        currentUser={currentUser}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
        onSelectConversation={handleSelectConversation}
      />

      <main className="chat-main-surface relative z-10 ml-72 flex h-full flex-col">
        <ChatHeader
          user={currentUser}
          conversationTitle={activeConversation?.title}
          onLogout={handleLogout}
          onToggleTheme={handleToggleTheme}
          theme={theme}
        />

        <ChatThread
          messages={activeMessages}
          dayChip={dayChip}
          isTyping={isTyping}
          errorMessage={errorMessage}
          userFirstName={firstNameFromUserName(currentUser?.user_name ?? '')}
          onStarterPrompt={handleSend}
        />

        <ChatInputDock
          placeholder="Hỏi về hướng nghiệp hoặc kỹ năng…"
          onSend={handleSend}
          disabled={isTyping}
          isStreaming={isTyping}
          onStop={handleStopStream}
          chatMode={chatMode}
          onChatModeChange={setChatMode}
        />
      </main>
    </div>
  )
}