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
      <div className="sidebar-inline-panel my-1 px-3 py-3">
        <input
          className="u-focus w-full rounded-xl border border-outline-variant/25 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface outline-none"
          onChange={(event) => setDraftTitle(event.target.value)}
          value={draftTitle}
        />
        {itemError && <p className="mt-2 text-xs text-error">{itemError}</p>}
        <div className="mt-2 flex justify-end gap-2">
          <button
            className="u-focus rounded-lg px-3 py-1 text-xs font-semibold text-on-surface/65 hover:bg-surface-container"
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
            className="u-focus rounded-lg bg-on-surface px-3 py-1 text-xs font-semibold text-surface-bright shadow-sm transition hover:bg-on-surface/88"
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
      <div className="sidebar-inline-panel my-1 px-3 py-3">
        <p className="text-xs font-medium text-on-surface/82">
          Delete <span className="font-semibold">"{label}"</span>?
        </p>
        <div className="mt-2 flex justify-end gap-2">
          <button
            className="u-focus rounded-lg border border-outline-variant/35 bg-surface-bright/70 px-3 py-1 text-xs font-semibold text-on-surface/75 shadow-sm transition hover:bg-surface-container-lowest"
            onClick={() => setIsDeleteConfirming(false)}
            type="button"
          >
            Cancel
          </button>
          <button
            className="u-focus rounded-lg bg-on-surface px-3 py-1 text-xs font-semibold text-surface-bright shadow-sm transition hover:bg-on-surface/88"
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
        'group flex min-h-[2.5rem] items-center gap-0.5 rounded-xl transition-colors',
        active ? 'bg-primary/14' : 'hover:bg-surface-container-high/50',
      ].join(' ')}
    >
      <button
        className="u-focus flex min-w-0 flex-1 items-center gap-2.5 rounded-xl py-2 pl-2.5 pr-1 text-left"
        onClick={onClick}
        title={label}
        type="button"
      >
        <span
          className={[
            'material-symbols-outlined shrink-0 text-[20px]',
            active ? 'text-primary' : 'text-on-surface/38',
          ].join(' ')}
          style={{ fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0" }}
        >
          chat_bubble
        </span>
        <span
          className={[
            'truncate text-[13px] leading-snug',
            active ? 'font-medium text-on-surface' : 'text-on-surface/65',
          ].join(' ')}
        >
          {label}
        </span>
      </button>

      <button
        aria-label="Rename conversation"
        className="u-focus mr-0.5 rounded-lg p-1.5 text-on-surface/38 opacity-0 transition hover:bg-surface-container group-hover:opacity-100"
        onClick={() => {
          setDraftTitle(label)
          setIsEditing(true)
        }}
        type="button"
      >
        <span className="material-symbols-outlined text-[17px]">edit</span>
      </button>
      <button
        aria-label="Delete conversation"
        className="u-focus mr-0.5 rounded-lg p-1.5 text-on-surface/38 opacity-0 transition hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100"
        onClick={() => setIsDeleteConfirming(true)}
        type="button"
      >
        <span className="material-symbols-outlined text-[17px]">delete</span>
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
      className="u-focus flex w-full items-center gap-2.5 rounded-xl border border-outline-variant/28 bg-surface-container-low/82 px-3 py-2 text-left text-[13px] font-medium text-on-surface/78 transition hover:bg-surface-container-lowest"
      onClick={() => navigate('/sync')}
      type="button"
    >
      <span className="material-symbols-outlined shrink-0 text-[18px] text-primary/85">
        cloud_upload
      </span>
      <span className="min-w-0 truncate">Sync documents</span>
    </button>
  )
}

function AdminViewDocsButton() {
  const navigate = useNavigate()
  return (
    <button
      className="u-focus flex w-full items-center gap-2.5 rounded-xl border border-outline-variant/28 bg-surface-container-low/82 px-3 py-2 text-left text-[13px] font-medium text-on-surface/78 transition hover:bg-surface-container-lowest"
      onClick={() => navigate('/admin/documents')}
      type="button"
    >
      <span className="material-symbols-outlined shrink-0 text-[18px] text-primary/85">
        folder_open
      </span>
      <span className="min-w-0 truncate">View documents</span>
    </button>
  )
}

function AdminCostLogsButton() {
  const navigate = useNavigate()
  return (
    <button
      className="u-focus flex w-full items-center gap-2.5 rounded-xl border border-outline-variant/28 bg-surface-container-low/82 px-3 py-2 text-left text-[13px] font-medium text-on-surface/78 transition hover:bg-surface-container-lowest"
      onClick={() => navigate('/admin/cost-logs')}
      type="button"
    >
      <span className="material-symbols-outlined shrink-0 text-[18px] text-primary/85">
        payments
      </span>
      <span className="min-w-0 truncate">Token usage</span>
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
    <nav className="sidebar-surface fixed left-0 top-0 z-50 flex h-full w-72 flex-col backdrop-blur-xl">
      <div className="shrink-0 px-3.5 pb-2 pt-3.5">
        <h1 className="font-headline text-[0.8125rem] font-semibold leading-tight tracking-tight text-on-surface">
          RecomMind Bot
        </h1>
        <p className="mt-1 text-[11px] leading-snug text-on-surface/42">
          Trợ lý hướng nghiệp
        </p>
        <button
          className="sidebar-new-convo-btn u-focus mt-3.5 flex h-10 w-full items-center justify-center gap-2 rounded-full px-4 text-[13px] font-medium transition active:scale-[0.99]"
          onClick={onNewChat}
          type="button"
        >
          <span className="material-symbols-outlined text-[20px]">add</span>
          Cuộc trò chuyện mới
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-2.5 pb-2 pt-1">
        <p className="shrink-0 px-1.5 pb-1.5 pt-1 text-[11px] font-medium text-on-surface/36">
          Gần đây
        </p>
        <div className="min-h-0 flex-1 space-y-0.5 overflow-y-auto pr-0.5">
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

      <div className="mt-auto shrink-0 space-y-2 px-3.5 pb-3.5 pt-2">
        {userRole === 'admin' ? (
          <div className="flex flex-col gap-1">
            <AdminSyncButton />
            <AdminViewDocsButton />
            <AdminCostLogsButton />
          </div>
        ) : null}

        <div className="flex items-center gap-2.5 rounded-2xl bg-surface-container-high/85 px-2.5 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary/26 to-primary/10 text-[11px] font-bold text-primary">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-medium leading-tight text-on-surface">
              {userName}
            </p>
            <p className="truncate text-[10px] font-medium uppercase tracking-wide text-on-surface/40">
              {userRole}
            </p>
          </div>
        </div>
      </div>
    </nav>
  )
}
