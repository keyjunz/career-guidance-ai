import { useMemo, useState } from 'react'

import { SideNav } from '../../components/layout/SideNav'
import { ChatHeader } from '../../components/layout/ChatHeader'
import { ChatThread } from '../../components/chat/ChatThread'
import { ChatInputDock } from '../../components/chat/ChatInputDock'
import type { ChatMessage } from '../../types/chat'
import { sendChatMessage } from '../../services/chatApi'
import { mapApiPayloadToAssistantMessage } from '../../mappers/chatMapper'

const seedMessages: ChatMessage[] = [
  {
    id: 'm1',
    role: 'assistant',
    authorLabel: 'Kinetic AI',
    variant: 'standard',
    text:
      'Welcome back to the Vault. Secure connection established. How can I assist you with your repositories today?',
    createdAtLabel: 'Today',
  },
  {
    id: 'm2',
    role: 'user',
    authorLabel: 'John Doe',
    text:
      'Pull the latest synthesis on career progression frameworks from the engineering talent pool dataset.',
  },
  {
    id: 'm3',
    role: 'assistant',
    authorLabel: 'Kinetic AI',
    variant: 'luminary',
    title: 'Synthesis Complete',
    text:
      'Cross-referencing 4,200 nodes within the engineering talent pool. The primary trajectory deviation over the last 18 months heavily favors dual-track specialization over traditional management routing.',
    actions: [
      { id: 'export', label: 'Export Data', icon: 'download', align: 'left' },
      { id: 'copy', label: 'Copy', icon: 'content_copy', align: 'right' },
    ],
    bento: [
      { label: 'Vector Alpha', value: 'Systems Architecture' },
      { label: 'Vector Beta', value: 'ML Infrastructure' },
    ],
  },
]

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(seedMessages)
  const [isTyping, setIsTyping] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [conversationId, setConversationId] = useState<string | undefined>(
    undefined,
  )

  const dayChip = useMemo(() => messages.find((m) => m.createdAtLabel)?.createdAtLabel, [messages])

  const handleSend = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isTyping) return

    setErrorMessage('')
    setIsTyping(true)

    const optimisticUserMessage: ChatMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      authorLabel: 'John Doe',
      text: trimmed,
    }
    setMessages((prev) => [...prev, optimisticUserMessage])

    try {
      const payload = await sendChatMessage({
        user_id: '550e8400-e29b-41d4-a716-446655440000',
        message: trimmed,
        conversation_id: conversationId,
      })

      setConversationId(payload.conversation_id)
      const assistantMessage = mapApiPayloadToAssistantMessage(payload)
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to connect chat API.'
      setErrorMessage(message)
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <div className="h-screen w-full overflow-hidden bg-surface text-on-surface kv-texture-overlay">
      <div className="absolute inset-0 z-0" />
      <SideNav />

      <main className="ml-72 flex h-full flex-col bg-surface relative z-10">
        <ChatHeader />

        <ChatThread
          messages={messages}
          dayChip={dayChip ?? 'Today'}
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

