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

    async detail(slug: string): Promise<RouteDetail> {
        const {data} = await api.get<RouteDetail>(`/routes/${slug}/`);
        return data;
    },

    async create(payload: RouteWritePayload): Promise<RouteDetail> {
        const {data} = await api.post<RouteDetail>('/routes/', payload);
        return data;
    },

    async update(slug: string, payload: Partial<RouteWritePayload>): Promise<RouteDetail> {
        const {data} = await api.patch<RouteDetail>(`/routes/${slug}/`, payload);
        return data;
    },

    async archive(slug: string): Promise<void> {
        await api.delete(`/routes/${slug}/`);
    },

    async submit(slug: string): Promise<RouteDetail> {
        const {data} = await api.post<RouteDetail>(`/routes/${slug}/submit/`);
        return data;
    },

    async copy(slug: string): Promise<RouteDetail> {
        const {data} = await api.post<RouteDetail>(`/routes/${slug}/copy/`);
        return data;
    },

    async addStop(slug: string, payload: {cultural_object: number; note?: string}): Promise<RouteStop> {
        const {data} = await api.post<RouteStop>(`/routes/${slug}/stops/`, payload);
        return data;
    },

    async removeStop(slug: string, stopId: number): Promise<void> {
        await api.delete(`/routes/${slug}/stops/${stopId}/`);
    },

    async reorder(slug: string, items: ReorderItem[]): Promise<void> {
        await api.post(`/routes/${slug}/reorder/`, {order: items});
    },

    async listMine(status?: RouteStatus): Promise<RouteListItem[]> {
        const {data} = await api.get<RouteListItem[]>('/users/me/routes/', {
            params: status ? {status} : undefined,
        });
        return data;
    },

    exportUrl(slug: string, format: 'gpx' | 'kml'): string {
        const base = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api';
        return `${base}/routes/${slug}/export/?format=${format}`;
    },
};
