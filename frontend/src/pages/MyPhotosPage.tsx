import {useState, useEffect} from 'react';
import {Link} from 'react-router';
import toast from 'react-hot-toast';
import {objectsService} from '../services/objects.service';
import {photosService} from '../services/photos.service';
import Lightbox from '../components/Objects/Lightbox';
import CoverImage from '../components/Objects/CoverImage';
import type {CulturalObjectWithMyPhotos, ObjectPhoto} from '../types';

const STATUS_OVERLAY: Record<string, {label: string; cls: string} | null> = {
    approved: null,
    pending: {label: 'На модерації', cls: 'bg-yellow-500/90'},
    rejected: {label: 'Відхилено', cls: 'bg-red-600/90'},
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
    const [caption, setCaption] = useState(photo.caption);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const original = photo.caption;
    const dirty = caption !== original;

    const handleDelete = async () => {
        if (!confirm('Видалити це фото? Дію не можна скасувати.')) return;
        setDeleting(true);
        try {
            await photosService.remove(objectId, photo.id);
            onDeleted(photo.id);
            toast.success('Фото видалено');
        } catch {
            toast.error('Не вдалося видалити фото');
            setDeleting(false);
        }
    };

    const handleSave = async () => {
        if (!dirty || saving) return;
        if (caption.length > 200) {
            toast.error('Підпис не може перевищувати 200 символів');
            return;
        }
        setSaving(true);
        try {
            const updated = await photosService.updateCaption(objectId, photo.id, caption);
            onUpdated(updated);
            toast.success(
                updated.status === 'pending' && photo.status !== 'pending'
                    ? 'Підпис оновлено. Фото на повторну модерацію.'
                    : 'Підпис оновлено'
            );
        } catch {
            toast.error('Не вдалося оновити підпис');
            setCaption(original);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className={`w-40 shrink-0 ${deleting ? 'opacity-50' : ''}`}>
            <div className="relative">
                <button
                    type="button"
                    onClick={onOpen}
                    className="relative w-40 h-32 block rounded overflow-hidden border border-gray-200 hover:border-amber-400 cursor-pointer"
                    title="Переглянути"
                >
                    <img
                        src={photo.thumbnail_url}
                        alt={photo.caption || ''}
                        loading="lazy"
                        className="w-full h-full object-cover"
                    />
                    {STATUS_OVERLAY[photo.status] && (
                        <span
                            className={`absolute bottom-0 left-0 right-0 ${STATUS_OVERLAY[photo.status]!.cls} text-white text-[10px] font-semibold text-center py-0.5 uppercase tracking-wide`}
                            aria-label={photo.status}
                        >
                            {STATUS_OVERLAY[photo.status]!.label}
                        </span>
                    )}
                </button>
                <button
                    type="button"
                    onClick={handleDelete}
                    disabled={deleting || saving}
                    className="absolute top-1 right-1 bg-red-600 hover:bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs cursor-pointer disabled:opacity-50"
                    aria-label="Видалити фото"
                    title="Видалити фото"
                >✕</button>
            </div>
            <input
                type="text"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                onBlur={handleSave}
                onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
                maxLength={200}
                placeholder="Без підпису"
                disabled={saving}
                className={`mt-1 w-full text-xs border rounded px-2 py-1 disabled:bg-gray-50 ${
                    dirty ? 'border-amber-400' : 'border-gray-200'
                }`}
            />
            {dirty && !saving && (
                <p className="text-[10px] text-amber-700 mt-0.5">Enter або клік-out → зберегти</p>
            )}
            {saving && (
                <p className="text-[10px] text-gray-500 mt-0.5">Збереження…</p>
            )}
        </div>
    );
}

export default function MyPhotosPage() {
    const [items, setItems] = useState<CulturalObjectWithMyPhotos[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lightbox, setLightbox] = useState<{photos: ObjectPhoto[]; idx: number} | null>(null);

    useEffect(() => {
        objectsService.getWithMyPhotos()
            .then(data => setItems(data.results))
            .catch(() => setError('Не вдалося завантажити список.'))
            .finally(() => setLoading(false));
    }, []);

    const handlePhotoUpdated = (objectId: number, updated: ObjectPhoto) => {
        setItems(prev => prev.map(obj => {
            if (obj.id !== objectId) return obj;
            return {
                ...obj,
                my_photos: obj.my_photos.map(p => p.id === updated.id ? updated : p),
            };
        }));
    };

    const handlePhotoDeleted = (objectId: number, photoId: number) => {
        setItems(prev => prev
            .map(obj => {
                if (obj.id !== objectId) return obj;
                return {...obj, my_photos: obj.my_photos.filter(p => p.id !== photoId)};
            })
            .filter(obj => obj.my_photos.length > 0)  // прибираємо об'єкт без фото
        );
    };

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
                    <p className="text-gray-600">Завантаження...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <p className="text-red-600">{error}</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Мої фото</h1>
                <p className="text-sm text-gray-500 mb-6">
                    Об'єкти, до яких ви додавали фото. Підпис можна редагувати — затверджене фото після зміни знов піде на модерацію.
                </p>

                {items.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500 mb-4">Ви ще не додавали фото до жодного об'єкта</p>
                        <Link to="/" className="text-amber-600 hover:text-amber-800 underline">
                            Перейти на карту
                        </Link>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {items.map(obj => {
                            const counts = countByStatus(obj.my_photos);
                            return (
                                <div
                                    key={obj.id}
                                    className="border border-gray-200 rounded-lg p-3 hover:border-amber-300 transition-colors"
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
                                                className="text-lg font-semibold text-gray-900 hover:text-amber-700 truncate block"
                                            >
                                                {obj.title}
                                            </Link>
                                            <div className="text-xs text-gray-500 mt-1">
                                                {obj.tags.map(t => t.icon).join(' ')} · автор {obj.author_name}
                                            </div>
                                            <div className="flex flex-wrap gap-2 mt-2 text-xs">
                                                <span className="text-gray-700">
                                                    Моїх фото: <strong>{obj.my_photos.length}</strong>
                                                </span>
                                                {counts.approved > 0 && (
                                                    <span className="text-green-700">✓ {counts.approved} затверджено</span>
                                                )}
                                                {counts.pending > 0 && (
                                                    <span className="text-yellow-700">⏳ {counts.pending} на модерації</span>
                                                )}
                                                {counts.rejected > 0 && (
                                                    <span className="text-red-700">✕ {counts.rejected} відхилено</span>
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
                    </div>
                )}
            </div>

            {lightbox && (
                <Lightbox
                    photos={lightbox.photos}
                    initialIndex={lightbox.idx}
                    onClose={() => setLightbox(null)}
                />
            )}
        </div>
    );
}
