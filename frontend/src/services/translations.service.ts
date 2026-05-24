import api from './api';
import type {MyTranslation} from '../types/translations';
import type {PaginatedResponse} from '../types';

export const translationsService = {
    listMine: (params?: {page?: number; page_size?: number}) =>
        api.get<PaginatedResponse<MyTranslation>>('/users/me/translations/', {params}).then(r => r.data),

    listMineByUrl: (url: string) =>
        api.get<PaginatedResponse<MyTranslation>>(url).then(r => r.data),
};
