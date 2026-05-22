import type {Tag} from './index';

export interface Visit {
    id: number;
    object_id: number;
    object_title: string;
    object_cover_url: string | null;
    object_tags: Tag[];
    visited_at: string;          // ISO date 'YYYY-MM-DD'
    impression: string;
    is_public: boolean;
    created_at: string;
    updated_at: string;
}

export interface PlannedVisit {
    id: number;
    object_id: number;
    object_title: string;
    object_cover_url: string | null;
    object_tags: Tag[];
    planned_date: string | null;
    note: string;
    created_at: string;
}

export interface VisitsStats {
    total_visits: number;
    total_approved_objects: number;
    completed_routes: number;
    by_tag: {id: number; name: string; icon: string; visited_count: number}[];
}

export interface VisitUpdate {
    impression?: string;
    visited_at?: string;
    is_public?: boolean;
}

export interface PlannedVisitUpdate {
    planned_date?: string | null;
    note?: string;
}
