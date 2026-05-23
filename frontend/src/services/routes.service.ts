import api from './api';
import type {
    RouteDetail, RouteListItem, RouteStatus, RouteStop,
    RouteWritePayload, ReorderItem,
} from '../types/routes';

interface ListFilters {
    is_featured?: boolean;
    tags?: number[];
    search?: string;
    duration_min?: number;
    duration_max?: number;
}

export const routesService = {
    async list(filters: ListFilters = {}): Promise<RouteListItem[]> {
        const params: Record<string, string> = {};
        if (filters.is_featured) params.is_featured = 'true';
        if (filters.tags?.length) params.tags = filters.tags.join(',');
        if (filters.search?.trim()) params.search = filters.search.trim();
        if (filters.duration_min != null) params.duration_min = String(filters.duration_min);
        if (filters.duration_max != null) params.duration_max = String(filters.duration_max);
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

    async markCompleted(id: number): Promise<{created_visits: number; total_stops: number}> {
        const {data} = await api.post(`/routes/${id}/mark-completed/`);
        return data;
    },

    async computeGeometry(id: number, profile?: 'foot-walking' | 'cycling-regular' | 'driving-car') {
        const {data} = await api.post<{geometry: [number, number][]; distance_m: number; duration_s: number}>(
            `/routes/${id}/compute-geometry/`,
            profile ? {profile} : {},
        );
        return data;
    },

    async optimizeOrder(id: number, profile?: 'foot-walking' | 'cycling-regular' | 'driving-car') {
        const {data} = await api.post<{new_order: number[]; stops_count: number; distance_m: number | null; duration_s: number | null}>(
            `/routes/${id}/optimize-order/`,
            profile ? {profile} : {},
        );
        return data;
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

    async updateStop(id: number, stopId: number, payload: {note?: string}): Promise<RouteStop> {
        const {data} = await api.patch<RouteStop>(`/routes/${id}/stops/${stopId}/`, payload);
        return data;
    },

    async reorder(id: number, items: ReorderItem[]): Promise<void> {
        await api.post(`/routes/${id}/reorder/`, {order: items});
    },

    async listMine(params?: {status?: RouteStatus; page?: number; page_size?: number}) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: RouteListItem[]}>(
            '/users/me/routes/', {params},
        );
        return data;
    },

    async listMineByUrl(url: string) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: RouteListItem[]}>(url);
        return data;
    },

    exportUrl(id: number, format: 'gpx' | 'kml' | 'kmz'): string {
        const base = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api';
        return `${base}/routes/${id}/export/?fmt=${format}`;
    },
};
