export interface AuthUser {
  id: number
  username: string
  display_name: string
}

export interface AuthResponse {
  user: AuthUser
}

export interface AuthLogoutResponse {
  ok: boolean
}

export interface RegisterPayload {
  username: string
  password: string
  display_name: string | null
}

export interface LoginPayload {
  username: string
  password: string
}

export interface ErrorResponse {
  detail: string | null
}

export interface DeleteAccountPayload {
  password: string
  confirmation: '注销账号'
}

