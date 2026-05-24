import {useCallback, useEffect, useState} from 'react';

export interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

interface Options<T> {
    initialFetch: () => Promise<PaginatedResponse<T>>;
    fetchByUrl: (url: string) => Promise<PaginatedResponse<T>>;
    onError?: (e: unknown) => void;
    /** Re-runs `initialFetch` when any of these change. */
    deps?: unknown[];
}

/**
 * Load-more pagination helper. Returns the current items, count, loading flags,
 * and `loadMore`/`setItems` for in-place mutations (delete/edit/restore).
 *
 * The hook intentionally strips the API host from the `next` URL before re-fetching
 * so the request goes through the configured `api` axios instance (which adds
 * authorization headers and uses `VITE_API_URL`).
 */
export function usePaginatedList<T>({initialFetch, fetchByUrl, onError, deps = []}: Options<T>) {
    const [items, setItems] = useState<T[]>([]);
    const [count, setCount] = useState(0);
    const [nextUrl, setNextUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [error, setError] = useState<unknown>(null);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(null);
        initialFetch()
            .then(data => {
                if (cancelled) return;
                setItems(data.results);
                setCount(data.count);
                setNextUrl(data.next);
            })
            .catch(e => {
                if (cancelled) return;
                setError(e);
                onError?.(e);
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);

    const loadMore = useCallback(async () => {
        if (!nextUrl || loadingMore) return;
        setLoadingMore(true);
        try {
            // DRF returns absolute URLs in `next`; strip the API host so axios uses its baseURL.
            const path = nextUrl.replace(/^https?:\/\/[^/]+\/api/, '');
            const data = await fetchByUrl(path);
            setItems(prev => [...prev, ...data.results]);
            setNextUrl(data.next);
            setCount(data.count);
        } catch (e) {
            onError?.(e);
        } finally {
            setLoadingMore(false);
        }
    }, [nextUrl, loadingMore, fetchByUrl, onError]);

    return {items, setItems, count, setCount, nextUrl, loading, loadingMore, error, loadMore};
}
