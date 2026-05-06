import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { AuthUser } from '../../types/api'
import type { ChatConversation } from '../../types/chat'

function ConversationItem({
  id,
  label,
  active,
  onClick,
  onRename,
  onDelete,
}: {
  id: string
  label: string
  active?: boolean
  onClick: () => void
  onRename: (conversationId: string, nextTitle: string) => void
  onDelete: (conversationId: string) => void
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [draftTitle, setDraftTitle] = useState(label)
  const [isDeleteConfirming, setIsDeleteConfirming] = useState(false)
  const [itemError, setItemError] = useState('')

  const saveRename = () => {
    const nextTitle = draftTitle.trim()
    if (!nextTitle) {
      setItemError('Title cannot be empty.')
      return
    }
    onRename(id, nextTitle)
    setIsEditing(false)
    setItemError('')
  }

  if (isEditing) {
    return (
      <div className="mx-2 my-1 rounded-lg border border-sky-400/30 bg-sky-500/10 px-3 py-3">
        <input
          className="w-full rounded-md border border-outline-variant/30 bg-surface px-3 py-2 text-sm text-on-surface outline-none focus:border-primary"
          onChange={(event) => setDraftTitle(event.target.value)}
          value={draftTitle}
        />
        {itemError && <p className="mt-2 text-xs text-red-300">{itemError}</p>}
        <div className="mt-2 flex justify-end gap-2">
          <button
            className="rounded-md px-3 py-1 text-xs font-semibold uppercase tracking-wider text-on-surface/70 hover:bg-white/5"
            onClick={() => {
              setDraftTitle(label)
              setItemError('')
              setIsEditing(false)
            }}
            type="button"
          >
            Cancel
          </button>
          <button
            className="rounded-md bg-primary px-3 py-1 text-xs font-semibold uppercase tracking-wider text-white hover:bg-sky-400"
            onClick={saveRename}
            type="button"
          >
            Save
          </button>
        </div>
      </div>
    )
  }

  if (isDeleteConfirming) {
    return (
      <div className="mx-2 my-1 rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-3">
        <p className="text-xs text-red-200">
          Delete <span className="font-semibold">"{label}"</span>?
        </p>
        <div className="mt-2 flex justify-end gap-2">
          <button
            className="rounded-md px-3 py-1 text-xs font-semibold uppercase tracking-wider text-on-surface/70 hover:bg-white/5"
            onClick={() => setIsDeleteConfirming(false)}
            type="button"
          >
            Cancel
          </button>
          <button
            className="rounded-md bg-red-500 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-white hover:bg-red-400"
            onClick={() => onDelete(id)}
            type="button"
          >
            Delete
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className={[
        'mx-2 my-1 flex items-center gap-2 rounded-lg px-3 py-2 transition-all duration-300 ease-out',
        active
          ? 'bg-gradient-to-r from-sky-500 to-sky-600 text-white shadow-[0_0_15px_rgba(56,189,248,0.30)]'
          : 'text-on-surface/60 hover:text-on-surface hover:bg-surface-container-high',
      ].join(' ')}
    >
      <button
        className="flex min-w-0 flex-1 items-center gap-3 rounded-md px-1 py-1 text-left"
        onClick={onClick}
        type="button"
      >
        <span className="material-symbols-outlined text-[20px]">chat</span>
        <span className="truncate text-sm font-medium">{label}</span>
      </button>

      <button
        aria-label="Rename conversation"
        className="rounded-md p-1 transition hover:bg-black/15"
        onClick={() => {
          setDraftTitle(label)
          setIsEditing(true)
        }}
        type="button"
      >
        <span className="material-symbols-outlined text-[18px]">edit</span>
      </button>
      <button
        aria-label="Delete conversation"
        className="rounded-md p-1 transition hover:bg-black/15"
        onClick={() => setIsDeleteConfirming(true)}
        type="button"
      >
        <span className="material-symbols-outlined text-[18px]">delete</span>
      </button>
    </div>
  )
}

type SideNavProps = {
  conversations: ChatConversation[]
  activeConversationId: string
  onSelectConversation: (conversationId: string) => void
  onRenameConversation: (conversationId: string, nextTitle: string) => void
  onDeleteConversation: (conversationId: string) => void
  onNewChat: () => void
  currentUser?: AuthUser | null
}

function getInitials(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return 'U'
  const parts = trimmed.split(/\s+/).slice(0, 2)
  return parts.map((part) => part[0]?.toUpperCase() || '').join('') || 'U'
}

function AdminSyncButton() {
  const navigate = useNavigate()
  return (
    <button
      className="mt-4 mx-2 mb-2 flex w-[calc(100%-1rem)] items-center gap-3 rounded-xl bg-surface-container px-4 py-3 border border-outline-variant/10 text-on-surface/70 transition hover:bg-surface-container-high hover:text-on-surface"
      onClick={() => navigate('/sync')}
      type="button"
    >
      <span className="material-symbols-outlined text-[20px] text-primary/70">cloud_upload</span>
      <span className="text-sm font-semibold">Sync Documents</span>
    </button>
  )
}

export function SideNav({
  conversations,
  activeConversationId,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  onNewChat,
  currentUser,
}: SideNavProps) {
  const userName = currentUser?.user_name ?? 'Guest User'
  const userRole = currentUser?.role ?? 'client'
  const initials = getInitials(userName)

  return (
    <nav className="fixed left-0 top-0 z-50 flex h-full w-72 flex-col overflow-y-auto rounded-r-2xl bg-surface-container-low py-8 shadow-[4px_0_40px_rgba(0,0,0,0.18)]">
      <div className="px-8 mb-8">
        <h1 className="font-headline text-lg font-bold tracking-tight text-sky-400 mb-1">
          Kinetic Assistant
        </h1>
        <p className="font-body text-sm text-on-surface/70">
          High-Security Sanctuary
        </p>
      </div>

      <div className="px-6 mb-8">
        <button
          className="chat-new-button w-full rounded-xl py-3 px-4 font-headline text-sm font-bold text-white transition-transform duration-200 active:scale-95"
          onClick={onNewChat}
          type="button"
        >
          <span className="inline-flex items-center justify-center gap-2">
            <span className="material-symbols-outlined text-[18px]">add</span>
            New Chat
          </span>
        </button>
      </div>

      <div className="flex-1 px-4 flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <p className="px-4 mb-2 text-[10px] font-semibold uppercase tracking-widest text-on-surface/60">
            Conversations
          </p>
          {conversations.map((conversation) => (
            <ConversationItem
              key={conversation.id}
              id={conversation.id}
              label={conversation.title}
              active={conversation.id === activeConversationId}
              onClick={() => onSelectConversation(conversation.id)}
              onRename={onRenameConversation}
              onDelete={() => onDeleteConversation(conversation.id)}
            />
          ))}
        </div>
      </div>

      <div className="px-4 mt-auto pt-6 relative">
        <div className="absolute left-8 right-8 top-0 h-px bg-outline-variant/10" />

        {userRole === 'admin' && <AdminSyncButton />}

        <div className="mt-4 mx-2 flex items-center gap-3 rounded-xl bg-surface-container-high px-4 py-3 border border-outline-variant/10">
          <div className="w-8 h-8 rounded-full bg-primary-container/20 flex items-center justify-center flex-shrink-0 text-primary">
            <span className="font-headline text-xs font-bold">{initials}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-on-surface">{userName}</span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-primary-dim">
              {userRole}
            </span>
          </div>
        </div>
      </div>
    </nav>
  )
}

