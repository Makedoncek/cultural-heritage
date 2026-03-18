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

export interface RegisterResponse {
    user: User;
    tokens: AuthTokens;
}

export interface Tag {
    id: number;
    name: string;
    slug: string;
    icon: string;
}

export interface CulturalObject {
    id: number;
    title: string;
    latitude: string;
    longitude: string;
    status: 'pending' | 'approved' | 'archived';
    author_name: string;
    tags: Tag[];
}

export interface CulturalObjectDetail {
    id: number;
    title: string;
    description: string;
    latitude: string;
    longitude: string;
    status: 'pending' | 'approved' | 'archived';
    author: string;
    tags: Tag[];
    wikipedia_url: string | null;
    official_website: string | null;
    google_maps_url: string | null;
    created_at: string;
    updated_at: string;
    archived_at: string | null;
}

export interface CulturalObjectWrite {
    title: string;
    description: string;
    latitude: number;
    longitude: number;
    tags: number[];
    wikipedia_url?: string;
    official_website?: string;
    google_maps_url?: string;
}

export interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}