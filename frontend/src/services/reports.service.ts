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

    async listMine(): Promise<InaccuracyReport[]> {
        const {data} = await api.get<InaccuracyReport[]>('/users/me/reports/');
        return data;
    },

    async listOnMyObjects(): Promise<InaccuracyReport[]> {
        const {data} = await api.get<InaccuracyReport[]>('/users/me/objects/reports/');
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
