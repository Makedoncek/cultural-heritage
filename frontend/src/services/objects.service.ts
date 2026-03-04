import api from "./api";
import type {CulturalObject, CulturalObjectDetail, CulturalObjectWrite, PaginatedResponse} from '../types';

interface ObjectFilters {
    tags?: string;
    search?: string;
}

export const objectsService = {
    getAll: (params?: ObjectFilters) =>
        api.get<PaginatedResponse<CulturalObject>>('/objects/', {params}).then(res => res.data),

    getById: (id: number) =>
        api.get<CulturalObjectDetail>(`/objects/${id}/`).then(res => res.data),

    create: (data: CulturalObjectWrite) =>
        api.post<CulturalObjectDetail>('/objects/', data).then(res => res.data),

    update: (id: number, data: Partial<CulturalObjectWrite>) =>
        api.patch<CulturalObjectDetail>(`/objects/${id}/`, data).then(res => res.data),

    delete: (id: number) =>
        api.delete(`/objects/${id}/`).then(res => res.data),

    getMy: () =>
        api.get<PaginatedResponse<CulturalObject>>('/objects/my/').then(res => res.data),
};