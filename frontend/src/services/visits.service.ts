import api from './api';
import type {Visit, VisitMapPoint, VisitsStats, VisitUpdate, PlannedVisit, PlannedVisitUpdate} from '../types/visits';

export const visitsService = {
    async toggle(objectId: number): Promise<{is_visited: boolean; visit?: Visit}> {
        const {data} = await api.post(`/objects/${objectId}/visit/`);
        return data;
    },

    async update(visitId: number, patch: VisitUpdate): Promise<Visit> {
        const {data} = await api.patch<Visit>(`/visits/${visitId}/`, patch);
        return data;
    },

    async count(objectId: number): Promise<number> {
        const {data} = await api.get<{visits_count: number}>(`/objects/${objectId}/visits-count/`);
        return data.visits_count;
    },

    async listMine(params?: {page?: number; page_size?: number}) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: Visit[]}>(
            '/users/me/visits/', {params},
        );
        return data;
    },

    async listMineByUrl(url: string) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: Visit[]}>(url);
        return data;
    },

    async listPublic(username: string, params?: {page?: number; page_size?: number}) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: Visit[]}>(
            `/users/${encodeURIComponent(username)}/visits/`, {params},
        );
        return data;
    },

    async listPublicByUrl(url: string) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: Visit[]}>(url);
        return data;
    },

    // All public visits as lightweight points — the author-profile map shows everything, not just the loaded page.
    async listPublicMap(username: string): Promise<VisitMapPoint[]> {
        const {data} = await api.get<VisitMapPoint[]>(`/users/${encodeURIComponent(username)}/visits/map/`);
        return data;
    },

    async stats(): Promise<VisitsStats> {
        const {data} = await api.get<VisitsStats>('/users/me/visits/stats/');
        return data;
    },
};

export const plannedVisitsService = {
    async toggle(objectId: number): Promise<{is_planned: boolean; planned?: PlannedVisit}> {
        const {data} = await api.post(`/objects/${objectId}/plan-visit/`);
        return data;
    },

    async update(plannedId: number, patch: PlannedVisitUpdate): Promise<PlannedVisit> {
        const {data} = await api.patch<PlannedVisit>(`/planned-visits/${plannedId}/`, patch);
        return data;
    },

    async convertToVisit(plannedId: number): Promise<{visit: Visit; created: boolean}> {
        const {data} = await api.post(`/planned-visits/${plannedId}/convert-to-visit/`);
        return data;
    },

    async listMine(params?: {page?: number; page_size?: number}) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: PlannedVisit[]}>(
            '/users/me/planned-visits/', {params},
        );
        return data;
    },

    async listMineByUrl(url: string) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: PlannedVisit[]}>(url);
        return data;
    },
};
