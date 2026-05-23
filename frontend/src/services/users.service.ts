import api from './api';
import type {AuthorProfile, CulturalObject, FollowToggleResponse} from '../types';

export const usersService = {
    getProfile: (username: string) =>
        api.get<AuthorProfile>(`/users/${username}/`).then(res => res.data),

    getObjects: (username: string) =>
        api.get<CulturalObject[]>(`/users/${username}/objects/`).then(res => res.data),

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
