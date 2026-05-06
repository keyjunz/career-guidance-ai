import type {
  AuthUser,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
} from '../types/api'
import { apiRequest } from './apiClient'
import { setAuthTokens } from './authStorage'

export async function login(payload: LoginRequest): Promise<TokenResponse> {
  const response = await apiRequest<TokenResponse>('/api/auth/login', {
    method: 'POST',
    body: payload,
    auth: false,
  })

  setAuthTokens(response.access_token, response.refresh_token)
  return response
}

export async function register(payload: RegisterRequest): Promise<AuthUser> {
  return apiRequest<AuthUser>('/api/auth/register', {
    method: 'POST',
    body: payload,
    auth: false,
  })
}

export async function getMe(): Promise<AuthUser> {
  return apiRequest<AuthUser>('/api/auth/me')
}
