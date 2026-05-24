import api from "./api";
import type {CulturalObject, CulturalObjectDetail, CulturalObjectWithMyPhotos, CulturalObjectWrite, PaginatedResponse, FavoriteToggleResponse} from '../types';

interface ObjectFilters {
    tags?: string;
    search?: string;
    page?: number;
    object_type?: string;
    event_status?: string;
}

export const objectsService = {
    getAll: (params?: ObjectFilters, signal?: AbortSignal) =>
        api.get<PaginatedResponse<CulturalObject>>('/objects/', {params, signal}).then(res => res.data),

    getById: (id: number, lang?: string) =>
        api.get<CulturalObjectDetail>(`/objects/${id}/`, lang ? {params: {lang}} : undefined).then(res => res.data),

    create: (data: CulturalObjectWrite) =>
        api.post<CulturalObjectDetail>('/objects/', data).then(res => res.data),

    update: (id: number, data: Partial<CulturalObjectWrite>) =>
        api.patch<CulturalObjectDetail>(`/objects/${id}/`, data).then(res => res.data),

    checkDuplicates: (latitude: number, longitude: number, excludeId?: number) =>
        api.post<{nearby: {id: number; title: string; latitude: string; longitude: string; distance_m: number}[]}>(
            '/objects/check-duplicates/',
            {latitude, longitude, exclude_id: excludeId},
        ).then(res => res.data),

    delete: (id: number) =>
        api.delete(`/objects/${id}/`).then(res => res.data),

    restore: (id: number) =>
        api.post(`/objects/${id}/restore/`).then(res => res.data),

    hardDelete: (id: number) =>
        api.delete(`/objects/${id}/hard-delete/`).then(res => res.data),

    getMy: (params?: {page?: number; page_size?: number}) =>
        api.get<PaginatedResponse<CulturalObject>>('/objects/my/', {params}).then(res => res.data),

    getMyByUrl: (url: string) =>
        api.get<PaginatedResponse<CulturalObject>>(url).then(res => res.data),

    toggleFavorite: (id: number) =>
        api.post<FavoriteToggleResponse>(`/objects/${id}/favorite/`).then(res => res.data),

    getFavorites: (params?: {page?: number; page_size?: number}) =>
        api.get<PaginatedResponse<CulturalObject>>('/objects/favorites/', {params}).then(res => res.data),

    getFavoritesByUrl: (url: string) =>
        api.get<PaginatedResponse<CulturalObject>>(url).then(res => res.data),

    getPopular: () =>
        api.get<CulturalObject[]>('/objects/popular/').then(res => res.data),

    getWithMyPhotos: (params?: {page?: number; page_size?: number}) =>
        api.get<PaginatedResponse<CulturalObjectWithMyPhotos>>(
            '/objects/with-my-photos/',
            {params},
        ).then(res => res.data),

    getWithMyPhotosByUrl: (url: string) =>
        api.get<PaginatedResponse<CulturalObjectWithMyPhotos>>(url).then(res => res.data),

    submitTranslation: (id: number, payload: {language: string; title: string; description: string}) =>
        api.post<{id: number; language: string; title: string; description: string; status: string}>(
            `/objects/${id}/translations/`, payload,
        ).then(res => res.data),
};