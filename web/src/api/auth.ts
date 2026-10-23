import { request } from './client'
import type {
  AuthLogoutResponse,
  DeleteAccountPayload,
  AuthResponse,
  LoginPayload,
  RegisterPayload,
} from './types'

export function registerAccount(payload: RegisterPayload): Promise<AuthResponse> {
  return request<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function loginAccount(payload: LoginPayload): Promise<AuthResponse> {
  return request<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getCurrentAccount(): Promise<AuthResponse> {
  return request<AuthResponse>('/api/auth/me')
}

export function logoutAccount(): Promise<AuthLogoutResponse> {
  return request<AuthLogoutResponse>('/api/auth/logout', { method: 'POST' })
}

export function deleteAccount(payload: DeleteAccountPayload): Promise<AuthLogoutResponse> {
  return request<AuthLogoutResponse>('/api/auth/account', {
    method: 'DELETE',
    body: JSON.stringify(payload),
  })
}
