import { Navigate, createBrowserRouter } from 'react-router-dom'

import { PlaceholderPage } from './PlaceholderPage'
import { ChatPage } from '../pages/chat/ChatPage'

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/chat" replace /> },
  { path: '/chat', element: <ChatPage /> },
  { path: '/login', element: <PlaceholderPage title="Login" /> },
  { path: '/register', element: <PlaceholderPage title="Register" /> },
  { path: '/sync', element: <PlaceholderPage title="Sync" /> },
])

