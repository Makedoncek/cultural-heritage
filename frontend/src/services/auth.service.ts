import api from './api'
import type {RegisterData, LoginData, MessageResponse, AuthTokens, PasswordResetData, PasswordResetConfirmData} from "../types";

export const authService = {
    register: (data: RegisterData) =>
        api.post<MessageResponse>('/auth/register/', data).then(res => res.data),

    login: (credentials: LoginData) =>
        api.post<AuthTokens>('/auth/login/', credentials).then(res => res.data),

    refresh: (refreshToken: string) =>
        api.post<AuthTokens>('/auth/refresh/', {refresh: refreshToken}).then(res => res.data),

    verifyEmail: (token: string) =>
        api.get<MessageResponse>(`/auth/verify-email/?token=${token}`).then(res => res.data),

    requestPasswordReset: (data: PasswordResetData) =>
        api.post<MessageResponse>('/auth/password-reset/', data).then(res => res.data),

    confirmPasswordReset: (data: PasswordResetConfirmData) =>
        api.post<MessageResponse>('/auth/password-reset/confirm/', data).then(res => res.data),

    resendVerification: (email: string) =>
        api.post<MessageResponse>('/auth/resend-verification/', {email}).then(res => res.data),
}
