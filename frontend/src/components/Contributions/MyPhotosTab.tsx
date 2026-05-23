import {useState} from 'react';
import {Link} from 'react-router';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {objectsService} from '../../services/objects.service';
import {photosService} from '../../services/photos.service';
import {usePaginatedList} from '../../hooks/usePaginatedList';
import LoadMoreButton from '../common/LoadMoreButton';
import Lightbox from '../Objects/Lightbox';
import CoverImage from '../Objects/CoverImage';
import type {CulturalObjectWithMyPhotos, ObjectPhoto} from '../../types';

const STATUS_OVERLAY_CLS: Record<string, string | null> = {
    approved: null,
    pending: 'bg-yellow-500/90',
    rejected: 'bg-red-600/90',
};

function countByStatus(photos: ObjectPhoto[]) {
    const c = {approved: 0, pending: 0, rejected: 0};
    photos.forEach(p => { c[p.status]++; });
    return c;
}

interface PhotoCardProps {
    objectId: number;
    photo: ObjectPhoto;
    onOpen: () => void;
    onUpdated: (updated: ObjectPhoto) => void;
    onDeleted: (photoId: number) => void;
}

function PhotoCard({objectId, photo, onOpen, onUpdated, onDeleted}: PhotoCardProps) {
    const {t} = useTranslation();
    const [caption, setCaption] = useState(photo.caption);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const original = photo.caption;
    const dirty = caption !== original;

    const handleDelete = async () => {
        if (!confirm(t('photo.deletePhoto'))) return;
        setDeleting(true);
        try {
            await photosService.remove(objectId, photo.id);
            onDeleted(photo.id);
            toast.success(t('photo.deleted'));
        } catch {
            toast.error(t('photo.deleteError'));
            setDeleting(false);
        }
    };

    const handleSave = async () => {
        if (!dirty || saving) return;
        if (caption.length > 200) {
            toast.error(t('photo.captionMaxLength'));
            return;
        }
        setSaving(true);
        try {
            const updated = await photosService.updateCaption(objectId, photo.id, caption);
            onUpdated(updated);
            toast.success(
                updated.status === 'pending' && photo.status !== 'pending'
                    ? t('photo.captionUpdatedModeration')
                    : t('photo.captionUpdated')
            );
        } catch {
            toast.error(t('photo.captionUpdateError'));
            setCaption(original);
        } finally {
            setSaving(false);
        }
    };

    const overlayCls = STATUS_OVERLAY_CLS[photo.status];
    const overlayLabel = photo.status === 'pending' ? t('photo.underReview')
        : photo.status === 'rejected' ? t('photo.rejected')
        : null;

    return (
        <div className={`w-40 shrink-0 ${deleting ? 'opacity-50' : ''}`}>
            <div className="relative">
                <button
                    type="button"
                    onClick={onOpen}
                    className="relative w-40 h-32 block rounded overflow-hidden border border-gray-200 dark:border-stone-700 hover:border-amber-400 dark:hover:border-amber-500 cursor-pointer"
                    title={t('myPhotos.viewLabel')}
                >
                    <img
                        src={photo.thumbnail_url}
                        alt={photo.caption || ''}
                        loading="lazy"
                        className="w-full h-full object-cover"
                    />
                    {overlayCls && overlayLabel && (
                        <span
                            className={`absolute bottom-0 left-0 right-0 ${overlayCls} text-white text-[10px] font-semibold text-center py-0.5 uppercase tracking-wide`}
                            aria-label={photo.status}
                        >
                            {overlayLabel}
                        </span>
                    )}
                </button>
                <button
                    type="button"
                    onClick={handleDelete}
                    disabled={deleting || saving}
                    className="absolute top-1 right-1 bg-red-600 hover:bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs cursor-pointer disabled:opacity-50"
                    aria-label={t('myPhotos.deletePhotoTitle')}
                    title={t('myPhotos.deletePhotoTitle')}
                >✕</button>
            </div>
            <input
                type="text"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                onBlur={handleSave}
                onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
                maxLength={200}
                placeholder={t('myPhotos.noCaption')}
                disabled={saving}
                className={`mt-1 w-full text-xs border rounded px-2 py-1 disabled:bg-gray-50 dark:disabled:bg-stone-900 bg-white dark:bg-stone-800 text-gray-900 dark:text-stone-100 placeholder-gray-400 dark:placeholder-stone-500 ${
                    dirty ? 'border-amber-400' : 'border-gray-200 dark:border-stone-600'
                }`}
            />
            {dirty && !saving && (
                <p className="text-[10px] text-amber-700 dark:text-amber-400 mt-0.5">{t('photo.captionSavePrompt')}</p>
            )}
            {saving && (
                <p className="text-[10px] text-gray-500 dark:text-stone-400 mt-0.5">{t('photo.captionSaving')}</p>
            )}
        </div>
    );
}

export default function MyPhotosTab() {
    const {t} = useTranslation();
    const {items, setItems, count: totalCount, nextUrl, loading, loadingMore, loadMore, error} = usePaginatedList<CulturalObjectWithMyPhotos>({
        initialFetch: () => objectsService.getWithMyPhotos(),
        fetchByUrl: (url) => objectsService.getWithMyPhotosByUrl(url),
        onError: () => toast.error(t('common.loadMoreError')),
        deps: [],
    });
    const [lightbox, setLightbox] = useState<{photos: ObjectPhoto[]; idx: number} | null>(null);

    const handlePhotoUpdated = (objectId: number, updated: ObjectPhoto) => {
        setItems(prev => prev.map(obj => {
            if (obj.id !== objectId) return obj;
            return {...obj, my_photos: obj.my_photos.map(p => p.id === updated.id ? updated : p)};
        }));
    };

    const handlePhotoDeleted = (objectId: number, photoId: number) => {
        setItems(prev => prev
            .map(obj => obj.id !== objectId ? obj : {...obj, my_photos: obj.my_photos.filter(p => p.id !== photoId)})
            .filter(obj => obj.my_photos.length > 0)
        );
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
            </div>
        );
    }
    if (error && items.length === 0) {
        return <p className="text-red-600 text-center py-6">{t('myPhotos.loadError')}</p>;
    }
    if (items.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500 dark:text-stone-400 mb-4">{t('myPhotos.empty')}</p>
                <Link to="/" className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 underline">
                    {t('myPhotos.goToMap')}
                </Link>
            </div>
        );
    }

    return (
        <>
            <div className="space-y-4">
                {items.map(obj => {
                    const counts = countByStatus(obj.my_photos);
                    return (
                        <div
                            key={obj.id}
                            className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-3 hover:border-amber-300 dark:hover:border-amber-500 transition-colors"
                        >
                            <div className="flex gap-3">
                                <Link to={`/objects/${obj.id}`} className="shrink-0">
                                    <CoverImage
                                        coverUrl={obj.cover_url}
                                        tags={obj.tags}
                                        alt={obj.title}
                                        className="w-24 h-24 rounded"
                                    />
                                </Link>
                                <div className="flex-1 min-w-0">
                                    <Link
                                        to={`/objects/${obj.id}`}
                                        className="text-lg font-semibold text-gray-900 dark:text-stone-100 hover:text-amber-700 dark:hover:text-amber-400 truncate block"
                                    >
                                        {obj.title}
                                    </Link>
                                    <p className="text-sm text-gray-600 dark:text-stone-300 mt-1">
                                        {t('myPhotos.authorByLine', {name: obj.author_name})}
                                    </p>
                                    {obj.tags.length > 0 && (
                                        <div className="flex flex-wrap gap-1.5 mt-2">
                                            {obj.tags.map(tag => (
                                                <span
                                                    key={tag.id}
                                                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded-full text-xs"
                                                >
                                                    {tag.icon} {tag.name}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                    <div className="flex flex-wrap gap-2 mt-2 text-xs">
                                        <span className="text-gray-700 dark:text-stone-200">
                                            {t('myPhotos.myPhotosCount')} <strong>{obj.my_photos.length}</strong>
                                        </span>
                                        {counts.approved > 0 && (
                                            <span className="text-green-700 dark:text-green-400">✓ {t('myPhotos.approvedCount', {count: counts.approved})}</span>
                                        )}
                                        {counts.pending > 0 && (
                                            <span className="text-yellow-700 dark:text-yellow-400">⏳ {t('myPhotos.pendingCount', {count: counts.pending})}</span>
                                        )}
                                        {counts.rejected > 0 && (
                                            <span className="text-red-700">✕ {t('myPhotos.rejectedCount', {count: counts.rejected})}</span>
                                        )}
                                    </div>
                                </div>
                            </div>
                            <div className="flex gap-3 mt-3 overflow-x-auto pb-1">
                                {obj.my_photos.map((p, i) => (
                                    <PhotoCard
                                        key={p.id}
                                        objectId={obj.id}
                                        photo={p}
                                        onOpen={() => setLightbox({photos: obj.my_photos, idx: i})}
                                        onUpdated={(u) => handlePhotoUpdated(obj.id, u)}
                                        onDeleted={(pid) => handlePhotoDeleted(obj.id, pid)}
                                    />
                                ))}
                            </div>
                        </div>
                    );
                })}
                <LoadMoreButton
                    show={!!nextUrl}
                    loading={loadingMore}
                    shown={items.length}
                    total={totalCount}
                    onClick={loadMore}
                />
            </div>
            {lightbox && (
                <Lightbox
                    photos={lightbox.photos}
                    initialIndex={lightbox.idx}
                    onClose={() => setLightbox(null)}
                />
            )}
        </>
    );
}
