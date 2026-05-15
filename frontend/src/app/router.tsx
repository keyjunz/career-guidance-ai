import { Navigate, createBrowserRouter } from 'react-router-dom'

import { ChatPage } from '../pages/chat/ChatPage'
import { LoginPage } from '../pages/auth/LoginPage'
import { RegisterPage } from '../pages/auth/RegisterPage'
import { SyncDocPage } from '../pages/sync/SyncDocPage'
import { AdminCostLogsPage } from '../pages/admin/AdminCostLogsPage'
import { AdminDocumentsPage } from '../pages/admin/AdminDocumentsPage'

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/chat" replace /> },
  { path: '/chat', element: <ChatPage /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  { path: '/sync', element: <SyncDocPage /> },
  { path: '/admin/documents', element: <AdminDocumentsPage /> },
  { path: '/admin/cost-logs', element: <AdminCostLogsPage /> },
])

