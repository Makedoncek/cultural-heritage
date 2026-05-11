import {useState} from 'react';
import {DndContext, closestCenter, type DragEndEvent} from '@dnd-kit/core';
import {SortableContext, useSortable, arrayMove, horizontalListSortingStrategy} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';
import toast from 'react-hot-toast';
import {photosService} from '../../services/photos.service';
import type {ObjectPhoto} from '../../types';

interface Props {
    objectId: number;
    photos: ObjectPhoto[];
    onPhotosChange: (photos: ObjectPhoto[]) => void;
}

function SortablePhoto({photo, onDelete}: {photo: ObjectPhoto; onDelete: () => void}) {
    const {attributes, listeners, setNodeRef, transform, transition} = useSortable({id: photo.id});
    const style = {transform: CSS.Transform.toString(transform), transition};

    return (
        <div ref={setNodeRef} style={style} className="relative w-32 flex-shrink-0">
            <div {...attributes} {...listeners} className="cursor-grab">
                <img src={photo.thumbnail_url} alt={photo.caption} className="w-32 h-24 object-cover rounded border"/>
                {photo.status === 'pending' && (
                    <span className="absolute bottom-1 left-1 right-1 bg-yellow-500 text-white text-[10px] text-center rounded">
                        На модерації
                    </span>
                )}
            </div>
            <button
                type="button"
                onClick={onDelete}
                className="absolute top-1 right-1 bg-red-600 hover:bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs cursor-pointer"
                aria-label="Видалити"
            >✕</button>
        </div>
    );
}

export default function ExistingPhotosManager({objectId, photos, onPhotosChange}: Props) {
    const authorPhotos = photos.filter(p => p.is_author_photo);
    const contribPhotos = photos.filter(p => !p.is_author_photo);
    const [reordering, setReordering] = useState(false);

    const handleDelete = async (id: number) => {
        if (!confirm('Видалити це фото?')) return;
        try {
            await photosService.remove(objectId, id);
            onPhotosChange(photos.filter(p => p.id !== id));
            toast.success('Фото видалено');
        } catch {
            toast.error('Не вдалося видалити');
        }
    };

    const handleDragEnd = async (e: DragEndEvent) => {
        const {active, over} = e;
        if (!over || active.id === over.id) return;
        const oldIdx = authorPhotos.findIndex(p => p.id === active.id);
        const newIdx = authorPhotos.findIndex(p => p.id === over.id);
        const reordered = arrayMove(authorPhotos, oldIdx, newIdx);
        const updatedAuthor = reordered.map((p, i) => ({...p, order: i}));
        onPhotosChange([...updatedAuthor, ...contribPhotos]);

        setReordering(true);
        try {
            await photosService.reorder(
                objectId,
                updatedAuthor.map(p => ({id: p.id, order: p.order})),
            );
        } catch {
            toast.error('Не вдалося зберегти порядок');
        } finally {
            setReordering(false);
        }
    };

    if (photos.length === 0) return null;

    return (
        <div className="my-4">
            {authorPhotos.length > 0 && (
                <>
                    <h3 className="font-semibold text-sm mb-2">Ваші фото</h3>
                    <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                        <SortableContext items={authorPhotos.map(p => p.id)} strategy={horizontalListSortingStrategy}>
                            <div className="flex gap-2 overflow-x-auto pb-2">
                                {authorPhotos.map(p => (
                                    <SortablePhoto key={p.id} photo={p} onDelete={() => handleDelete(p.id)}/>
                                ))}
                            </div>
                        </SortableContext>
                    </DndContext>
                    {reordering && <p className="text-xs text-gray-500">Збереження порядку…</p>}
                </>
            )}

            {contribPhotos.length > 0 && (
                <>
                    <h3 className="font-semibold text-sm mt-4 mb-2">Фото від спільноти</h3>
                    <div className="flex gap-2 overflow-x-auto pb-2">
                        {contribPhotos.map(p => (
                            <div key={p.id} className="w-32 flex-shrink-0">
                                <img src={p.thumbnail_url} alt="" className="w-32 h-24 object-cover rounded border"/>
                                <p className="text-xs text-gray-500 mt-1 truncate">@{p.uploaded_by.username}</p>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}
