import api from './api';
import type {
    RouteDetail, RouteListItem, RouteStatus, RouteStop,
    RouteWritePayload, ReorderItem,
} from '../types/routes';

interface ListFilters {
    is_featured?: boolean;
    tags?: number[];
}

export const routesService = {
    async list(filters: ListFilters = {}): Promise<RouteListItem[]> {
        const params: Record<string, string> = {};
        if (filters.is_featured) params.is_featured = 'true';
        if (filters.tags?.length) params.tags = filters.tags.join(',');
        const {data} = await api.get<RouteListItem[] | {results: RouteListItem[]}>('/routes/', {params});
        return Array.isArray(data) ? data : (data.results ?? []);
    },

    async detail(id: number): Promise<RouteDetail> {
        const {data} = await api.get<RouteDetail>(`/routes/${id}/`);
        return data;
    },

    async create(payload: RouteWritePayload): Promise<RouteDetail> {
        const {data} = await api.post<RouteDetail>('/routes/', payload);
        return data;
    },

    async update(id: number, payload: Partial<RouteWritePayload>): Promise<RouteDetail> {
        const {data} = await api.patch<RouteDetail>(`/routes/${id}/`, payload);
        return data;
    },

    async archive(id: number): Promise<void> {
        await api.delete(`/routes/${id}/`);
    },

    async restore(id: number): Promise<RouteDetail> {
        const {data} = await api.post<RouteDetail>(`/routes/${id}/restore/`);
        return data;
    },

    async hardDelete(id: number): Promise<void> {
        await api.delete(`/routes/${id}/hard-delete/`);
    },

    async submit(id: number): Promise<RouteDetail> {
        const {data} = await api.post<RouteDetail>(`/routes/${id}/submit/`);
        return data;
    },

    async copy(id: number): Promise<RouteDetail> {
        const {data} = await api.post<RouteDetail>(`/routes/${id}/copy/`);
        return data;
    },

    async addStop(id: number, payload: {cultural_object: number; note?: string}): Promise<RouteStop> {
        const {data} = await api.post<RouteStop>(`/routes/${id}/stops/`, payload);
        return data;
    },

    async removeStop(id: number, stopId: number): Promise<void> {
        await api.delete(`/routes/${id}/stops/${stopId}/`);
    },

    async reorder(id: number, items: ReorderItem[]): Promise<void> {
        await api.post(`/routes/${id}/reorder/`, {order: items});
    },

    async listMine(status?: RouteStatus): Promise<RouteListItem[]> {
        const {data} = await api.get<RouteListItem[]>('/users/me/routes/', {
            params: status ? {status} : undefined,
        });
        return data;
    },

    exportUrl(id: number, format: 'gpx' | 'kml'): string {
        const base = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api';
        return `${base}/routes/${id}/export/?fmt=${format}`;
    },
};
