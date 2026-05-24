import api from './api';
import type {MyTranslation} from '../types/translations';
import type {PaginatedResponse} from '../types';

export const translationsService = {
    listMine: (params?: {page?: number; page_size?: number; status?: string}) =>
        api.get<PaginatedResponse<MyTranslation>>('/users/me/translations/', {params}).then(r => r.data),

    listMineByUrl: (url: string) =>
        api.get<PaginatedResponse<MyTranslation>>(url).then(r => r.data),

    remove: (kind: 'object' | 'route', id: number) =>
        api.delete(`/translations/${kind}/${id}/`).then(r => r.data),

    archive: (kind: 'object' | 'route', id: number) =>
        api.post(`/translations/${kind}/${id}/archive/`).then(r => r.data),

    restore: (kind: 'object' | 'route', id: number) =>
        api.post(`/translations/${kind}/${id}/restore/`).then(r => r.data),

    edit: (kind: 'object' | 'route', id: number, payload: {title: string; description: string}) =>
        api.patch(`/translations/${kind}/${id}/`, payload).then(r => r.data),
};
