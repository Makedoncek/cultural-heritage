export type AudioLanguage = 'uk' | 'en' | 'pl' | 'de';
export type AudioStatus = 'pending' | 'approved' | 'rejected';

export interface AudioUploadedBy {
    id: number;
    username: string;
}

export interface ObjectAudio {
    id: number;
    cultural_object: number;
    uploaded_by: AudioUploadedBy;
    cloudinary_url: string;
    duration_seconds: number;
    language: AudioLanguage;
    language_label: string;
    title: string;
    narrator_name: string;
    status: AudioStatus;
    status_label: string;
    moderation_note: string;
    plays_count: number;
    created_at: string;
}

export interface AudioUploadPayload {
    audio: File;
    language: AudioLanguage;
    title: string;
    narrator_name?: string;
    copyright_confirmed: boolean;
}

export interface ObjectWithMyAudios {
    id: number;
    title: string;
    tags: {id: number; name: string; icon: string}[];
    author_name: string;
    my_audios: ObjectAudio[];
}
