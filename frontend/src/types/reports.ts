export type ReportReasonType =
    | 'wrong_coords'
    | 'wrong_name'
    | 'wrong_description'
    | 'wrong_tags'
    | 'duplicate'
    | 'other';

export type ReportStatus = 'pending' | 'resolved' | 'dismissed';

export interface InaccuracyReport {
    id: number;
    object_id: number;
    object_title: string;
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
    reason_type: ReportReasonType;
    note?: string;
}
