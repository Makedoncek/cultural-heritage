import api from './api';

export type Language = 'uk' | 'en';

export const preferenceService = {
    async get(): Promise<Language> {
        const {data} = await api.get<{language: Language}>('/me/preference/');
        return data.language;
    },

    async update(language: Language): Promise<Language> {
        const {data} = await api.patch<{language: Language}>('/me/preference/', {language});
        return data.language;
    },
};
