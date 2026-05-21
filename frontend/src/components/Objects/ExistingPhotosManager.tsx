import {useState} from 'react';
import {DndContext, closestCenter, type DragEndEvent} from '@dnd-kit/core';
import {SortableContext, useSortable, arrayMove, horizontalListSortingStrategy} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {photosService} from '../../services/photos.service';
import {useAuth} from '../../context/AuthContext';
import type {ObjectPhoto} from '../../types';

interface Props {
    objectId: number;
    photos: ObjectPhoto[];
    onPhotosChange: (photos: ObjectPhoto[]) => void;
}

function SortablePhoto({photo, canDelete, onDelete, underReviewLabel}: {photo: ObjectPhoto; canDelete: boolean; onDelete: () => void; underReviewLabel: string}) {
    const {attributes, listeners, setNodeRef, transform, transition} = useSortable({id: photo.id});
    const style = {transform: CSS.Transform.toString(transform), transition};

    return (
        <div ref={setNodeRef} style={style} className="relative w-32 flex-shrink-0">
            <div {...attributes} {...listeners} className="cursor-grab">
                <img src={photo.thumbnail_url} alt={photo.caption} className="w-32 h-24 object-cover rounded border"/>
                {photo.status === 'pending' && (
                    <span className="absolute bottom-1 left-1 right-1 bg-yellow-500 text-white text-[10px] text-center rounded">
                        {underReviewLabel}
                    </span>
                )}
                {!photo.is_author_photo && (
                    <span className="absolute top-1 left-1 bg-blue-600 text-white text-[10px] px-1.5 py-0.5 rounded">
                        @{photo.uploaded_by.username}
                    </span>
                )}
            </div>
            {canDelete && (
                <button
                    type="button"
                    onClick={onDelete}
                    className="absolute top-1 right-1 bg-red-600 hover:bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs cursor-pointer"
                    aria-label="Remove"
                >✕</button>
            )}
        </div>
    );
}

export default function ExistingPhotosManager({objectId, photos, onPhotosChange}: Props) {
    const {t} = useTranslation();
    const {user} = useAuth();
    const [reordering, setReordering] = useState(false);
    const canDeletePhoto = (p: ObjectPhoto) =>
        !!user && (user.is_staff || user.username === p.uploaded_by.username);

    const handleDelete = async (id: number) => {
        if (!confirm(t('photo.deletePhotoConfirm'))) return;
        try {
            await photosService.remove(objectId, id);
            onPhotosChange(photos.filter(p => p.id !== id));
            toast.success(t('photo.deleteSuccess'));
        } catch {
            toast.error(t('photo.deleteFail'));
        }
    };

    const handleDragEnd = async (e: DragEndEvent) => {
        const {active, over} = e;
        if (!over || active.id === over.id) return;
        const oldIdx = photos.findIndex(p => p.id === active.id);
        const newIdx = photos.findIndex(p => p.id === over.id);
        const reordered = arrayMove(photos, oldIdx, newIdx);
        const updated = reordered.map((p, i) => ({...p, order: i}));
        onPhotosChange(updated);

        setReordering(true);
        try {
            await photosService.reorder(
                objectId,
                updated.map(p => ({id: p.id, order: p.order})),
            );
        } catch {
            toast.error(t('photo.reorderFail'));
        } finally {
            setReordering(false);
        }
    };

    if (photos.length === 0) return null;

    return (
        <div className="my-4">
            <h3 className="font-semibold text-sm mb-2 text-gray-900 dark:text-stone-100">{t('photo.allPhotos')}</h3>
            <p className="text-xs text-gray-500 dark:text-stone-400 mb-2">{t('photo.reorderHintFull')}</p>
            <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={photos.map(p => p.id)} strategy={horizontalListSortingStrategy}>
                    <div className="flex gap-2 overflow-x-auto pb-2">
                        {photos.map(p => (
                            <SortablePhoto
                                key={p.id}
                                photo={p}
                                canDelete={canDeletePhoto(p)}
                                onDelete={() => handleDelete(p.id)}
                                underReviewLabel={t('photo.underReview')}
                            />
                        ))}
                    </div>
                </SortableContext>
            </DndContext>
            {reordering && <p className="text-xs text-gray-500 dark:text-stone-400">{t('photo.savingOrder')}</p>}
        </div>
    );
}
