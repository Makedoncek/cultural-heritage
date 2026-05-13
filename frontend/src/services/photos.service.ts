import {AxiosError} from 'axios';
import api from './api';
import type {ObjectPhoto, ReorderItem} from '../types';

export function extractUploadError(err: unknown): string {
    if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string' && detail.length > 0) return detail;
        const status = err.response?.status;
        if (status === 429) return 'перевищено ліміт завантажень (10/год)';
        if (status === 413) return 'файл занадто великий';
        if (status === 401) return 'потрібна авторизація';
        if (status === 403) return 'немає прав на завантаження';
        if (status === 404) return 'об\'єкт не знайдено';
        if (status && status >= 500) return 'помилка сервера, спробуйте пізніше';
        if (err.code === 'ERR_NETWORK') return 'немає з\'єднання';
    }
    return 'невідома помилка';
}

export const photosService = {
    upload: (objectId: number, image: File, caption: string = '', onProgress?: (pct: number) => void) => {
        const formData = new FormData();
        formData.append('image', image);
        if (caption) formData.append('caption', caption);

        return api.post<ObjectPhoto>(
            `/objects/${objectId}/photos/`,
            formData,
            {
                headers: {'Content-Type': 'multipart/form-data'},
                onUploadProgress: (e) => {
                    if (onProgress && e.total) {
                        onProgress(Math.round((e.loaded * 100) / e.total));
                    }
                },
            }
        ).then(r => r.data);
    },

    list: (objectId: number) =>
        api.get<ObjectPhoto[]>(`/objects/${objectId}/photos/`).then(r => r.data),

    remove: (objectId: number, photoId: number) =>
        api.delete(`/objects/${objectId}/photos/${photoId}/`).then(r => r.data),

    updateCaption: (objectId: number, photoId: number, caption: string) =>
        api.patch<ObjectPhoto>(
            `/objects/${objectId}/photos/${photoId}/`,
            {caption}
        ).then(r => r.data),

    reorder: (objectId: number, items: ReorderItem[]) =>
        api.post(`/objects/${objectId}/photos/reorder/`, {order: items}).then(r => r.data),
};
