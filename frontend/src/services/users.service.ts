import api from './api';
import type {AuthorProfile, CulturalObject, FollowToggleResponse} from '../types';

export const usersService = {
    getProfile: (username: string) =>
        api.get<AuthorProfile>(`/users/${username}/`).then(res => res.data),

    getObjects: (username: string) =>
        api.get<CulturalObject[]>(`/users/${username}/objects/`).then(res => res.data),

    toggleFollow: (username: string) =>
        api.post<FollowToggleResponse>(`/users/${username}/follow/`).then(res => res.data),

    getFavoriteAuthors: () =>
        api.get<AuthorProfile[]>('/users/favorite-authors/').then(res => res.data),
};
