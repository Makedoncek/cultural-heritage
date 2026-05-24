export type TranslationStatus = 'pending' | 'approved' | 'rejected' | 'archived';
export type TranslationKind = 'object' | 'route';

export interface MyTranslation {
    id: number;
    kind: TranslationKind;
    target_id: number;
    target_title: string;
    target_url: string;
    language: 'uk' | 'en' | 'pl' | 'de';
    title: string;
    status: TranslationStatus;
    reviewer_note: string;
    created_at: string;
    updated_at: string;
}
