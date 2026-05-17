import type {Tag} from './index';

export type RouteStatus = 'draft' | 'pending' | 'approved' | 'archived';

export interface RouteStop {
    id: number;
    order: number;
    object_id: number;
    object_title: string;
    latitude: string;
    longitude: string;
    object_status: 'pending' | 'approved' | 'archived';
    object_cover_url: string | null;
    note: string;
    is_unavailable: boolean;
}

export interface RouteListItem {
    id: number;
    slug: string;
    title: string;
    description: string;
    status: RouteStatus;
    is_featured: boolean;
    cover_photo: string;
    estimated_duration_minutes: number | null;
    author_name: string;
    tags: Tag[];
    stops_count: number;
    created_at: string;
    updated_at: string;
}

export interface RouteDetail extends RouteListItem {
    stops: RouteStop[];
    copied_from: string | null;
}

export interface RouteWritePayload {
    title: string;
    description: string;
    tags?: number[];
    cover_photo?: string;
    estimated_duration_minutes?: number | null;
}

export interface ReorderItem {
    id: number;
    order: number;
}
