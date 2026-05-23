import api from './api';
import type {AudioLanguage, AudioUploadPayload, ObjectAudio, ObjectWithMyAudios} from '../types/audio';

export const audioService = {
    async list(objectId: number, language?: AudioLanguage): Promise<ObjectAudio[]> {
        const {data} = await api.get<ObjectAudio[]>(`/objects/${objectId}/audios/`, {
            params: language ? {language} : undefined,
        });
        return data;
    },

    async upload(objectId: number, payload: AudioUploadPayload): Promise<ObjectAudio> {
        const fd = new FormData();
        fd.append('audio', payload.audio);
        fd.append('language', payload.language);
        fd.append('title', payload.title);
        if (payload.narrator_name) fd.append('narrator_name', payload.narrator_name);
        fd.append('copyright_confirmed', String(payload.copyright_confirmed));
        const {data} = await api.post<ObjectAudio>(`/objects/${objectId}/audios/`, fd, {
            headers: {'Content-Type': 'multipart/form-data'},
        });
        return data;
    },

    async update(objectId: number, audioId: number,
                 payload: Partial<Pick<ObjectAudio, 'title' | 'narrator_name' | 'language'>>): Promise<ObjectAudio> {
        const {data} = await api.patch<ObjectAudio>(`/objects/${objectId}/audios/${audioId}/`, payload);
        return data;
    },

    async remove(objectId: number, audioId: number): Promise<void> {
        await api.delete(`/objects/${objectId}/audios/${audioId}/`);
    },

    async incrementPlayCount(objectId: number, audioId: number): Promise<void> {
        await api.post(`/objects/${objectId}/audios/${audioId}/play/`);
    },

    async listMine(params?: {page?: number; page_size?: number}) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: ObjectWithMyAudios[]}>(
            '/objects/with-my-audios/', {params},
        );
        return data;
    },

    async listMineByUrl(url: string) {
        const {data} = await api.get<{count: number; next: string | null; previous: string | null; results: ObjectWithMyAudios[]}>(url);
        return data;
    },
};
