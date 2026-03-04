import api from './api'
import type {RegisterData, LoginData, RegisterResponse, AuthTokens} from "../types";

export const authService = {
    register: (data: RegisterData) =>
        api.post<RegisterResponse>('/auth/register/', data).then(res => res.data),

    login: (credentials: LoginData) =>
        api.post<AuthTokens>('/auth/login/', credentials).then(res => res.data),

    refresh: (refreshToken: string) =>
        api.post<AuthTokens>('/auth/refresh/', {refresh: refreshToken}).then(res => res.data),

}