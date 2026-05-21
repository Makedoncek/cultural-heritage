import api from './api';

export type Language = 'uk' | 'en';
export type Theme = 'light' | 'dark';

export interface UserPreference {
    language: Language;
    theme: Theme;
}

export type PreferenceUpdate = Partial<UserPreference>;

export const preferenceService = {
    async get(): Promise<UserPreference> {
        const {data} = await api.get<UserPreference>('/me/preference/');
        return data;
    },

    async update(patch: PreferenceUpdate | Language): Promise<UserPreference> {
        // Legacy call signature support: preferenceService.update('en') still works
        const body: PreferenceUpdate = typeof patch === 'string' ? {language: patch} : patch;
        const {data} = await api.patch<UserPreference>('/me/preference/', body);
        return data;
    },
};
