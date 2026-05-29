import {useEffect} from 'react';
import {Link} from 'react-router';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {objectsService} from '../../services/objects.service';
import {usePaginatedList} from '../../hooks/usePaginatedList';
import LoadMoreButton from '../Common/LoadMoreButton';
import FavoriteButton from '../Objects/FavoriteButton';
import type {CulturalObject} from '../../types';

interface Props {
    onCountChange?: (count: number) => void;
}

export default function FavoriteObjectsTab({onCountChange}: Props) {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const {items: objects, setItems: setObjects, count: totalCount, nextUrl, loading, loadingMore, loadMore, error} = usePaginatedList<CulturalObject>({
        initialFetch: () => objectsService.getFavorites(),
        fetchByUrl: (url) => objectsService.getFavoritesByUrl(url),
        onError: () => toast.error(t('common.loadMoreError')),
        deps: [],
    });

    useEffect(() => { onCountChange?.(totalCount); }, [totalCount, onCountChange]);

    const handleUnfavorited = (id: number) => {
        setObjects(prev => {
            const next = prev.filter(obj => obj.id !== id);
            onCountChange?.(next.length);
            return next;
        });
    };

    if (loading) return <div className="flex justify-center py-8"><div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/></div>;
    if (error && objects.length === 0) return <p className="text-red-600 text-center py-6">{t('favorites.loadError')}</p>;
    if (objects.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500 dark:text-stone-400 mb-4">{t('favorites.empty')}</p>
                <Link to="/" className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 underline">
                    {t('favorites.goToMap')}
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {objects.map(obj => (
                <div
                    key={obj.id}
                    className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                >
                    <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                            <span className="text-gray-900 dark:text-stone-100 font-medium">{obj.title}</span>
                            {obj.object_type === 'event' && (
                                <span className="px-2 py-0.5 text-xs font-medium rounded bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-300">
                                    {t('object.objectType.event')}
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-stone-400 mt-1">
                            {obj.tags.length > 0 && (
                                <span>{obj.tags.map(tg => tg.icon).join(' ')}</span>
                            )}
                            <span>{new Date(obj.created_at).toLocaleDateString(dateLocale)}</span>
                        </div>
                    </div>
                    <div className="flex gap-2 flex-wrap shrink-0">
                        <FavoriteButton
                            objectId={obj.id}
                            initialFavorited={true}
                            initialCount={obj.favorites_count ?? 0}
                            onToggle={(favorited) => { if (!favorited) handleUnfavorited(obj.id); }}
                        />
                        <Link
                            to={`/objects/${obj.id}`}
                            className="px-3 py-1.5 text-sm bg-amber-500 hover:bg-amber-600 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg"
                        >
                            {t('myObjects.view')}
                        </Link>
                    </div>
                </div>
            ))}
            <LoadMoreButton
                show={!!nextUrl}
                loading={loadingMore}
                shown={objects.length}
                total={totalCount}
                onClick={loadMore}
            />
        </div>
    );
}
