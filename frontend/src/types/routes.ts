import type {Tag} from './index';

export type RouteStatus = 'draft' | 'pending' | 'approved' | 'archived';
export type RouteVisibility = 'private' | 'public';

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
    is_visited: boolean;
}

export interface RouteListItem {
    id: number;
    title: string;
    description: string;
    status: RouteStatus;
    visibility: RouteVisibility;
    is_featured: boolean;
    cover_photo: string;
    estimated_duration_minutes: number | null;
    author_name: string;
    tags: Tag[];
    stops_count: number;
    created_at: string;
    updated_at: string;
    original_language: 'uk' | 'en' | 'pl' | 'de';
    translation_missing: boolean;
}

export interface RouteDetail extends RouteListItem {
    stops: RouteStop[];
    copied_from: number | null;
    route_geometry: [number, number][] | null;
    route_distance_m: number | null;
    route_duration_s: number | null;
    geometry_updated_at: string | null;
    available_languages: ('uk' | 'en' | 'pl' | 'de')[];
}

export interface RouteWritePayload {
    title: string;
    description: string;
    visibility?: RouteVisibility;
    tags?: number[];
    cover_photo?: string;
    estimated_duration_minutes?: number | null;
}

export interface ReorderItem {
    id: number;
    order: number;
}
