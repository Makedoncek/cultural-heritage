export type ReportReasonType =
    | 'wrong_coords'
    | 'wrong_name'
    | 'wrong_description'
    | 'wrong_tags'
    | 'duplicate'
    | 'spam'
    | 'offensive'
    | 'copyright'
    | 'broken_media'
    | 'other';

export type ReportTargetType = 'object' | 'route' | 'photo' | 'audio' | 'object_translation' | 'route_translation';

export type ReportStatus = 'pending' | 'resolved' | 'dismissed';

export interface InaccuracyReport {
    id: number;
    target_type: ReportTargetType | null;
    target_title: string;
    target_url: string | null;
    reporter_username: string;
    reason_type: ReportReasonType;
    reason_label: string;
    note: string;
    status: ReportStatus;
    status_label: string;
    admin_response: string;
    created_at: string;
    resolved_at: string | null;
}

export interface CreateReportPayload {
    target_type: ReportTargetType;
    target_id: number;
    reason_type: ReportReasonType;
    note?: string;
}

// Which reasons are offered for each content type.
export const REASONS_BY_TARGET: Record<ReportTargetType, ReportReasonType[]> = {
    object: ['wrong_coords', 'wrong_name', 'wrong_description', 'wrong_tags', 'duplicate', 'spam', 'other'],
    route: ['wrong_name', 'wrong_description', 'duplicate', 'spam', 'offensive', 'other'],
    photo: ['offensive', 'copyright', 'broken_media', 'wrong_description', 'other'],
    audio: ['offensive', 'copyright', 'broken_media', 'other'],
    object_translation: ['wrong_name', 'wrong_description', 'spam', 'offensive', 'other'],
    route_translation: ['wrong_name', 'wrong_description', 'spam', 'offensive', 'other'],
};
