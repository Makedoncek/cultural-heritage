import {useCallback, useState} from 'react';
import {useDropzone, type FileRejection} from 'react-dropzone';
import {DndContext, closestCenter, type DragEndEvent} from '@dnd-kit/core';
import {SortableContext, useSortable, arrayMove, horizontalListSortingStrategy} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';

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
    photo, onCaption, onRemove,
}: {
    photo: PendingPhoto;
    onCaption: (c: string) => void;
    onRemove: () => void;
}) {
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
                aria-label="Видалити"
            >✕</button>
            <input
                type="text"
                value={photo.caption}
                onChange={(e) => onCaption(e.target.value)}
                maxLength={200}
                placeholder="Підпис (опц.)"
                className="mt-1 w-full text-xs border rounded px-1 py-0.5"
            />
        </div>
    );
}

export default function PhotoUploader({photos, onChange, maxCount, label}: Props) {
    const [error, setError] = useState<string | null>(null);

    const onDrop = useCallback(async (accepted: File[]) => {
        setError(null);
        const allowed = maxCount - photos.length;
        if (allowed <= 0) {
            setError(`Максимум ${maxCount} фото.`);
            return;
        }

        const errors: string[] = [];
        if (accepted.length > allowed) {
            errors.push(`Прийнято ${allowed} з ${accepted.length} фото — досягнуто ліміту ${maxCount}.`);
        }

        const candidates = accepted.slice(0, allowed);
        const checks = await Promise.all(candidates.map(async (f) => {
            if (f.size > MAX_SIZE_MB * 1024 * 1024) {
                errors.push(`«${f.name}» перевищує ${MAX_SIZE_MB} MB.`);
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
                errors.push(`«${f.name}» не є валідним зображенням.`);
                return null;
            }
            return {
                id: `${Date.now()}-${Math.random()}`,
                file: f,
                previewUrl: url,
                caption: '',
            } satisfies PendingPhoto;
        }));

        const valid = checks.filter((p): p is PendingPhoto => p !== null);
        if (errors.length > 0) setError(errors.join(' '));
        if (valid.length > 0) onChange([...photos, ...valid]);
    }, [photos, maxCount, onChange]);

    const onDropRejected = useCallback((rejections: FileRejection[]) => {
        const msgs = rejections.map(r => {
            const reason = r.errors[0]?.code;
            if (reason === 'file-too-large') return `«${r.file.name}» перевищує ${MAX_SIZE_MB} MB.`;
            if (reason === 'file-invalid-type') return `«${r.file.name}» — непідтримуваний формат (потрібен JPG/PNG/WebP).`;
            if (reason === 'too-many-files') return `Забагато файлів — максимум ${maxCount}.`;
            return `«${r.file.name}» — ${r.errors[0]?.message || 'не прийнято'}.`;
        });
        setError(msgs.join(' '));
    }, [maxCount]);

    const {getRootProps, getInputProps, isDragActive} = useDropzone({
        onDrop,
        onDropRejected,
        accept: ACCEPTED,
        maxSize: MAX_SIZE_MB * 1024 * 1024,
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
            {label && <label className="block text-sm font-medium mb-2">{label}</label>}
            <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded p-6 text-center cursor-pointer ${
                    isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                }`}
            >
                <input {...getInputProps()} />
                <p className="text-sm text-gray-600">
                    📷 Перетягніть до {maxCount} фото або клікніть<br/>
                    <span className="text-xs">JPG, PNG, WebP до {MAX_SIZE_MB} MB</span>
                </p>
            </div>
            {error && <p className="text-red-600 text-sm mt-2">{error}</p>}

            {photos.length > 0 && (
                <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                    <SortableContext items={photos.map(p => p.id)} strategy={horizontalListSortingStrategy}>
                        <div className="flex gap-2 mt-3 overflow-x-auto pb-2">
                            {photos.map((p) => (
                                <SortableItem
                                    key={p.id}
                                    photo={p}
                                    onCaption={(c) => onChange(photos.map(x => x.id === p.id ? {...x, caption: c} : x))}
                                    onRemove={() => {
                                        URL.revokeObjectURL(p.previewUrl);
                                        onChange(photos.filter(x => x.id !== p.id));
                                    }}
                                />
                            ))}
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                            Перетягніть для зміни порядку. Перше фото = обкладинка.
                        </p>
                    </SortableContext>
                </DndContext>
            )}
        </div>
    );
}
