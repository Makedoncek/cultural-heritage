import {useCallback, useState} from 'react';
import {useDropzone, type FileRejection} from 'react-dropzone';
import {DndContext, closestCenter, type DragEndEvent} from '@dnd-kit/core';
import {SortableContext, useSortable, arrayMove, horizontalListSortingStrategy} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';
import {useTranslation} from 'react-i18next';

const MAX_SIZE_MB = 5;
const ACCEPTED = {'image/jpeg': [], 'image/png': [], 'image/webp': []};

export interface PendingPhoto {
    id: string;
    file: File;
    previewUrl: string;
    caption: string;
}

interface Props {
    photos: PendingPhoto[];
    onChange: (photos: PendingPhoto[]) => void;
    maxCount: number;
    label?: string;
}

function SortableItem({
    photo, onCaption, onRemove, captionPlaceholder,
}: Readonly<{
    photo: PendingPhoto;
    onCaption: (c: string) => void;
    onRemove: () => void;
    captionPlaceholder: string;
}>) {
    const {attributes, listeners, setNodeRef, transform, transition} = useSortable({id: photo.id});
    const style = {transform: CSS.Transform.toString(transform), transition};

    return (
        <div ref={setNodeRef} style={style} className="relative w-32 flex-shrink-0">
            <div {...attributes} {...listeners} className="cursor-grab">
                <img src={photo.previewUrl} alt="" className="w-32 h-24 object-cover rounded border"/>
            </div>
            <button
                type="button"
                onClick={onRemove}
                className="absolute top-1 right-1 bg-red-600 hover:bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs cursor-pointer"
                aria-label="Remove"
            >✕</button>
            <input
                type="text"
                value={photo.caption}
                onChange={(e) => onCaption(e.target.value)}
                maxLength={200}
                placeholder={captionPlaceholder}
                className="mt-1 w-full text-xs border border-gray-200 dark:border-stone-600 bg-white dark:bg-stone-800 text-gray-900 dark:text-stone-100 placeholder-gray-400 dark:placeholder-stone-500 rounded px-1 py-0.5"
            />
        </div>
    );
}

export default function PhotoUploader({photos, onChange, maxCount, label}: Readonly<Props>) {
    const {t} = useTranslation();
    const [error, setError] = useState<string | null>(null);

    const onDrop = useCallback(async (accepted: File[]) => {
        setError(null);
        const allowed = maxCount - photos.length;
        if (allowed <= 0) {
            setError(t('photo.limitReached', {count: maxCount}));
            return;
        }

        const errors: string[] = [];
        if (accepted.length > allowed) {
            errors.push(t('photo.acceptedSummary', {accepted: allowed, total: accepted.length, limit: maxCount}));
        }

        const candidates = accepted.slice(0, allowed);
        const checks = await Promise.all(candidates.map(async (f) => {
            if (f.size > MAX_SIZE_MB * 1024 * 1024) {
                errors.push(t('photo.fileTooLarge', {name: f.name, size: MAX_SIZE_MB}));
                return null;
            }
            const url = URL.createObjectURL(f);
            const isImage = await new Promise<boolean>((resolve) => {
                const img = new Image();
                img.onload = () => resolve(true);
                img.onerror = () => resolve(false);
                img.src = url;
            });
            if (!isImage) {
                URL.revokeObjectURL(url);
                errors.push(t('photo.invalidImage', {name: f.name}));
                return null;
            }
            return {
                id: crypto.randomUUID(),
                file: f,
                previewUrl: url,
                caption: '',
            } satisfies PendingPhoto;
        }));

        const valid = checks.filter((p): p is PendingPhoto => p !== null);
        if (errors.length > 0) setError(errors.join(' '));
        if (valid.length > 0) onChange([...photos, ...valid]);
    }, [photos, maxCount, onChange, t]);

    const onDropRejected = useCallback((rejections: FileRejection[]) => {
        const messages = rejections.map(r => {
            const code = r.errors[0]?.code;
            if (code === 'file-too-large') return t('photo.fileTooLarge', {name: r.file.name, size: MAX_SIZE_MB});
            if (code === 'file-invalid-type') return t('photo.wrongFormat', {name: r.file.name});
            if (code === 'too-many-files') return t('photo.tooManyFiles', {count: maxCount});
            return `«${r.file.name}» — ${r.errors[0]?.message || 'error'}.`;
        });
        setError(messages.join(' '));
    }, [maxCount, t]);

    const {getRootProps, getInputProps, isDragActive} = useDropzone({
        onDrop, onDropRejected, accept: ACCEPTED, maxSize: MAX_SIZE_MB * 1024 * 1024,
    });

    const handleDragEnd = (event: DragEndEvent) => {
        const {active, over} = event;
        if (over && active.id !== over.id) {
            const oldIdx = photos.findIndex(p => p.id === active.id);
            const newIdx = photos.findIndex(p => p.id === over.id);
            onChange(arrayMove(photos, oldIdx, newIdx));
        }
    };

    return (
        <div>
            {label && <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-stone-200">{label}</label>}
            <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded p-6 text-center cursor-pointer ${
                    isDragActive ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/40' : 'border-gray-300 dark:border-stone-600 bg-white dark:bg-stone-800'
                }`}
            >
                <input {...getInputProps()} />
                <p className="text-sm text-gray-600 dark:text-stone-300">
                    {t('photo.dragOrClick', {count: maxCount})}<br/>
                    <span className="text-xs">{t('photo.limits', {size: MAX_SIZE_MB})}</span>
                </p>
            </div>
            {error && <p className="text-red-600 dark:text-red-400 text-sm mt-2">{error}</p>}

            {photos.length > 0 && (
                <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                    <SortableContext items={photos.map(p => p.id)} strategy={horizontalListSortingStrategy}>
                        <div className="flex gap-2 mt-3 overflow-x-auto pb-2">
                            {photos.map((p) => (
                                <SortableItem
                                    key={p.id}
                                    photo={p}
                                    captionPlaceholder={t('photo.captionPlaceholder')}
                                    onCaption={(c) => onChange(photos.map(x => x.id === p.id ? {...x, caption: c} : x))}
                                    onRemove={() => {
                                        URL.revokeObjectURL(p.previewUrl);
                                        onChange(photos.filter(x => x.id !== p.id));
                                    }}
                                />
                            ))}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-stone-400 mt-1">
                            {t('photo.reorderHint')}
                        </p>
                    </SortableContext>
                </DndContext>
            )}
        </div>
    );
}
