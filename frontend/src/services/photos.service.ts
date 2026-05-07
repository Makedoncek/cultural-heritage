import api from './api';
import type {ObjectPhoto, ReorderItem} from '../types';

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
