import api from './api';
import type {AuthorProfile, CulturalObject, FollowToggleResponse, PaginatedResponse} from '../types';

export const usersService = {
    getProfile: (username: string) =>
        api.get<AuthorProfile>(`/users/${username}/`).then(res => res.data),

    getObjects: (username: string, params?: {page?: number; page_size?: number}) =>
        api.get<PaginatedResponse<CulturalObject>>(`/users/${username}/objects/`, {params}).then(res => res.data),

    getObjectsByUrl: (url: string) =>
        api.get<PaginatedResponse<CulturalObject>>(url).then(res => res.data),

    toggleFollow: (username: string) =>
        api.post<FollowToggleResponse>(`/users/${username}/follow/`).then(res => res.data),

    getFavoriteAuthors: (params?: {page?: number; page_size?: number}) =>
        api.get<{count: number; next: string | null; previous: string | null; results: AuthorProfile[]}>(
            '/users/favorite-authors/', {params},
        ).then(res => res.data),

    getFavoriteAuthorsByUrl: (url: string) =>
        api.get<{count: number; next: string | null; previous: string | null; results: AuthorProfile[]}>(url)
            .then(res => res.data),
};
