import api from './api';
import type {CreateReportPayload, InaccuracyReport} from '../types/reports';

export const reportsService = {
    async create(objectId: number, payload: CreateReportPayload): Promise<InaccuracyReport> {
        const {data} = await api.post<InaccuracyReport>(`/objects/${objectId}/report/`, payload);
        return data;
    },

    async deleteOwn(reportId: number): Promise<void> {
        await api.delete(`/reports/${reportId}/`);
    },

    async listMine(params?: {page?: number; page_size?: number}) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: InaccuracyReport[]}>(
            '/users/me/reports/', {params},
        );
        return data;
    },

    async listMineByUrl(url: string) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: InaccuracyReport[]}>(url);
        return data;
    },

    async listOnMyObjects(params?: {page?: number; page_size?: number}) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: InaccuracyReport[]}>(
            '/users/me/objects/reports/', {params},
        );
        return data;
    },

    async listOnMyObjectsByUrl(url: string) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: InaccuracyReport[]}>(url);
        return data;
    },

    async adminList(status: 'pending' | 'resolved' | 'dismissed' = 'pending'): Promise<InaccuracyReport[]> {
        const {data} = await api.get<InaccuracyReport[]>('/admin/reports/', {params: {status}});
        return data;
    },

    async adminResolve(reportId: number, adminResponse: string): Promise<InaccuracyReport> {
        const {data} = await api.post<InaccuracyReport>(
            `/admin/reports/${reportId}/resolve/`,
            {admin_response: adminResponse},
        );
        return data;
    },

    async adminDismiss(reportId: number, adminResponse: string): Promise<InaccuracyReport> {
        const {data} = await api.post<InaccuracyReport>(
            `/admin/reports/${reportId}/dismiss/`,
            {admin_response: adminResponse},
        );
        return data;
    },
};
