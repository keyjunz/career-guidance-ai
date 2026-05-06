import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { SideNav } from '../../components/layout/SideNav'
import { ChatHeader } from '../../components/layout/ChatHeader'
import { ChatThread } from '../../components/chat/ChatThread'
import { ChatInputDock } from '../../components/chat/ChatInputDock'
import type { ChatConversation, ChatMessage } from '../../types/chat'
import type { AuthUser } from '../../types/api'
import { sendChatMessage, streamChatMessage } from '../../services/chatApi'
import { mapApiPayloadToAssistantMessage } from '../../mappers/chatMapper'
import { clearAuthTokens, getAccessToken } from '../../services/authStorage'
import { getMe } from '../../services/authApi'

const BOT_LABEL = 'Kinetic AI'
const THEME_STORAGE_KEY = 'career_guidance_theme'

function createId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function createEmptyConversation(): ChatConversation {
  return {
    id: createId('conv'),
    title: 'New conversation',
    createdAt: new Date().toISOString(),
    messages: [],
  }
}

export function ChatPage() {
  const navigate = useNavigate()
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    return stored === 'dark' ? 'dark' : 'light'
  })
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null)
  const [conversations, setConversations] = useState<ChatConversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string>('')
  const [apiTypingConversationId, setApiTypingConversationId] = useState<string | null>(
    null,
  )

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId),
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

  const isTyping = activeConversationId === apiTypingConversationId

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  }, [theme])

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
          const initialConversation = createEmptyConversation()
          setConversations([initialConversation])
          setActiveConversationId(initialConversation.id)
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

  const handleNewChat = () => {
    const nextConversation = createEmptyConversation()
    setConversations((prev) => [nextConversation, ...prev])
    setActiveConversationId(nextConversation.id)
    setErrorMessage('')
  }

  const handleSelectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId)
    setErrorMessage('')
  }

  const handleRenameConversation = (conversationId: string, nextTitle: string) => {
    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, title: nextTitle }
          : conversation,
      ),
    )
  }

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
  }

  const handleLogout = () => {
    clearAuthTokens()
    navigate('/login', { replace: true })
  }

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'))
  }

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

    try {
      try {
        let streamedText = ''
        let streamedExecutionId: string | undefined
        let latestStatus = ''
        await streamChatMessage(
          { question: trimmed },
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
              const statusText = `Dang xu ly: ${status}`
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
          },
        )

        setConversations((prev) =>
          prev.map((conversation) =>
            conversation.id === activeConversationId
              ? {
                  ...conversation,
                  messages: conversation.messages.map((message) =>
                    message.id === streamingAssistantId
                      ? {
                          ...message,
                          text:
                            message.text.trim() ||
                            (latestStatus
                              ? `Dang xu ly: ${latestStatus}`
                              : 'No text response from server.'),
                          meta: {
                            executionId: streamedExecutionId,
                          },
                        }
                      : message,
                  ),
                }
              : conversation,
          ),
        )
        return
      } catch {
        // Remove temporary stream bubble before sync fallback.
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

      try {
        const payload = await sendChatMessage({
          question: trimmed,
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
      }
    } finally {
      setApiTypingConversationId((prev) =>
        prev === activeConversationId ? null : prev,
      )
    }
  }

  if (isCheckingAuth) {
    return (
      <div className="grid h-screen place-items-center bg-surface text-on-surface">
        <div className="rounded-3xl border border-outline-variant/15 bg-surface-container-high/80 px-8 py-6 text-sm font-semibold text-primary shadow-[0_30px_100px_rgba(0,0,0,0.45)]">
          Verifying secure session...
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen w-full overflow-hidden bg-surface text-on-surface kv-texture-overlay">
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

      <main className="ml-72 flex h-full flex-col bg-surface relative z-10">
        <ChatHeader
          user={currentUser}
          onLogout={handleLogout}
          onToggleTheme={handleToggleTheme}
          theme={theme}
        />

        <ChatThread
          messages={activeMessages}
          dayChip={dayChip}
          isTyping={isTyping}
          errorMessage={errorMessage}
        />

        <ChatInputDock
          placeholder="Ask about career guidance..."
          onSend={handleSend}
          disabled={isTyping}
        />
      </main>
    </div>
  )
}

