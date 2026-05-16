export interface User {
    id: number;
    username: string;
    email?: string;
    is_staff?: boolean;
}

export interface AuthTokens {
    access: string;
    refresh: string;
}

export interface RegisterData {
    username: string;
    email: string;
    password: string;
    password2: string;
}

export interface LoginData {
    username: string;
    password: string;
}

export interface MessageResponse {
    message: string;
}

export interface PasswordResetData {
    email: string;
}

export interface PasswordResetConfirmData {
    uid: string;
    token: string;
    password: string;
    password2: string;
}

export interface Tag {
    id: number;
    name: string;
    slug: string;
    icon: string;
    tag_type: 'object' | 'event';
}

export interface CulturalObject {
    id: number;
    title: string;
    latitude: string;
    longitude: string;
    status: 'pending' | 'approved' | 'archived';
    object_type: 'permanent' | 'event';
    event_start_date: string | null;
    event_end_date: string | null;
    author_name: string;
    tags: Tag[];
    created_at: string;
    is_favorited?: boolean;
    favorites_count?: number;
    cover_url?: string | null;
    is_visited?: boolean;
}

export interface FavoriteToggleResponse {
    is_favorited: boolean;
    favorites_count: number;
}

export interface CulturalObjectDetail {
    id: number;
    title: string;
    description: string;
    latitude: string;
    longitude: string;
    status: 'pending' | 'approved' | 'archived';
    object_type: 'permanent' | 'event';
    event_start_date: string | null;
    event_end_date: string | null;
    author: string;
    tags: Tag[];
    wikipedia_url: string | null;
    official_website: string | null;
    google_maps_url: string | null;
    created_at: string;
    updated_at: string;
    archived_at: string | null;
    is_favorited?: boolean;
    favorites_count?: number;
    photos?: ObjectPhoto[];
    photo_count?: number;
    cover_url?: string | null;
    is_visited?: boolean;
    is_planned?: boolean;
    visits_count?: number;
}

export interface PhotoUploadedBy {
    id: number;
    username: string;
}

export interface ObjectPhoto {
    id: number;
    cultural_object: number;
    uploaded_by: PhotoUploadedBy;
    image_url: string;
    thumbnail_url: string;
    caption: string;
    status: 'pending' | 'approved' | 'rejected';
    order: number;
    is_author_photo: boolean;
    created_at: string;
}

export interface ReorderItem {
    id: number;
    order: number;
}

export interface CulturalObjectWithMyPhotos extends CulturalObject {
    my_photos: ObjectPhoto[];
}

export interface CulturalObjectWrite {
    title: string;
    description: string;
    latitude: number;
    longitude: number;
    tags: number[];
    object_type?: 'permanent' | 'event';
    event_start_date?: string | null;
    event_end_date?: string | null;
    wikipedia_url?: string;
    official_website?: string;
    google_maps_url?: string;
}

export interface ObjectFormData {
    title: string;
    description: string;
    tags: number[];
    object_type: 'permanent' | 'event';
    event_start_date: string;
    event_end_date: string;
    latitude: number | null;
    longitude: number | null;
    wikipedia_url: string;
    official_website: string;
    google_maps_url: string;
}

export interface AuthorProfile {
    username: string;
    date_joined: string;
    approved_objects_count: number;
    total_favorites_received: number;
    followers_count: number;
    is_followed: boolean;
    email?: string | null;
}

export interface FollowToggleResponse {
    is_followed: boolean;
    followers_count: number;
}

export interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}