import {useEffect, useState} from 'react';
import {Link, useNavigate, useParams} from 'react-router';
import toast from 'react-hot-toast';
import {DndContext, closestCenter, type DragEndEvent} from '@dnd-kit/core';
import {SortableContext, useSortable, arrayMove, verticalListSortingStrategy} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';
import {useTranslation} from 'react-i18next';
import {routesService} from '../services/routes.service';
import {objectsService} from '../services/objects.service';
import {tagsService} from '../services/tags.service';
import type {RouteDetail, RouteStop, RouteVisibility} from '../types/routes';
import type {CulturalObject, Tag} from '../types';

function SortableStopItem({
    stop, onRemove, onNoteSave, dragHint, archivedHint, notePlaceholder, saveLabel, savingLabel,
}: Readonly<{
    stop: RouteStop;
    onRemove: () => void;
    onNoteSave: (note: string) => Promise<void>;
    dragHint: string;
    archivedHint: string;
    notePlaceholder: string;
    saveLabel: string;
    savingLabel: string;
}>) {
    const {attributes, listeners, setNodeRef, transform, transition, isDragging} = useSortable({id: stop.id});
    const [expanded, setExpanded] = useState(false);
    const [noteDraft, setNoteDraft] = useState(stop.note || '');
    const [savingNote, setSavingNote] = useState(false);

    useEffect(() => {
        setNoteDraft(stop.note || '');
    }, [stop.note]);

    const dirty = noteDraft !== (stop.note || '');
    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    const handleSave = async () => {
        setSavingNote(true);
        try {
            await onNoteSave(noteDraft);
            setExpanded(false);
        } finally {
            setSavingNote(false);
        }
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg"
        >
            <div className="flex items-center gap-2 px-3 py-2">
                <span {...attributes} {...listeners} className="cursor-grab text-gray-400 dark:text-stone-500 text-lg select-none" title={dragHint}>⋮⋮</span>
                <div className="shrink-0 w-7 h-7 rounded-full bg-amber-600 dark:bg-amber-500 text-white dark:text-stone-900 flex items-center justify-center font-bold text-sm">
                    {stop.order}
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-stone-100 truncate">
                        {stop.object_title}
                    </p>
                    {stop.is_unavailable && (
                        <p className="text-xs text-red-600 dark:text-red-400">{archivedHint}</p>
                    )}
                    {!expanded && stop.note && (
                        <p className="text-xs text-gray-600 dark:text-stone-400 italic mt-0.5 line-clamp-2">
                            {stop.note}
                        </p>
                    )}
                </div>
                <button
                    type="button"
                    onClick={() => setExpanded(e => !e)}
                    className={`shrink-0 text-sm px-2 cursor-pointer ${stop.note ? 'text-amber-600 dark:text-amber-400' : 'text-gray-400 dark:text-stone-500'} hover:text-amber-800 dark:hover:text-amber-300`}
                    title={notePlaceholder}
                >
                    📝
                </button>
                <button
                    type="button"
                    onClick={onRemove}
                    className="shrink-0 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 text-sm px-2 cursor-pointer"
                >
                    ✕
                </button>
            </div>
            {expanded && (
                <div className="px-3 pb-2 border-t border-gray-100 dark:border-stone-700">
                    <textarea
                        value={noteDraft}
                        onChange={(e) => setNoteDraft(e.target.value)}
                        maxLength={500}
                        rows={2}
                        placeholder={notePlaceholder}
                        className="w-full mt-2 bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
                    />
                    <div className="flex justify-between items-center mt-1">
                        <span className="text-xs text-gray-400 dark:text-stone-500">{noteDraft.length} / 500</span>
                        <button
                            type="button"
                            onClick={handleSave}
                            disabled={!dirty || savingNote}
                            className="px-2.5 py-1 text-xs bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded cursor-pointer disabled:opacity-50"
                        >
                            {savingNote ? savingLabel : saveLabel}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default function AddEditRoutePage() {
    const {id} = useParams<{id: string}>();
    const routeId = id ? Number(id) : null;
    const isEdit = routeId !== null;
    const navigate = useNavigate();
    const {t} = useTranslation();

    const [route, setRoute] = useState<RouteDetail | null>(null);
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [visibility, setVisibility] = useState<RouteVisibility>('private');
    const [durationHours, setDurationHours] = useState<string>('');
    const [selectedTags, setSelectedTags] = useState<number[]>([]);
    const [stops, setStops] = useState<RouteStop[]>([]);
    const [allTags, setAllTags] = useState<Tag[]>([]);
    const [loading, setLoading] = useState(isEdit);
    const [saving, setSaving] = useState(false);

    // Object picker
    const [search, setSearch] = useState('');
    const [searchResults, setSearchResults] = useState<CulturalObject[]>([]);
    const [searching, setSearching] = useState(false);

    useEffect(() => {
        tagsService.getAll().then(r => setAllTags(r.results)).catch(() => {});
    }, []);

    useEffect(() => {
        if (!isEdit || routeId == null) return;
        routesService.detail(routeId)
            .then(r => {
                setRoute(r);
                setTitle(r.title);
                setDescription(r.description);
                setVisibility(r.visibility);
                setDurationHours(r.estimated_duration_minutes ? String(Math.round(r.estimated_duration_minutes / 60 * 10) / 10) : '');
                setSelectedTags(r.tags.map(t => t.id));
                setStops(r.stops);
            })
            .catch(() => toast.error(t('routes.toast.loadFailed')))
            .finally(() => setLoading(false));
    }, [isEdit, routeId, t]);

    const handleSaveBasics = async (): Promise<RouteDetail | null> => {
        if (!title.trim() || !description.trim()) {
            toast.error(t('routes.toast.fillTitleDescription'));
            return null;
        }
        const payload = {
            title: title.trim(),
            description: description.trim(),
            visibility,
            tags: selectedTags,
            estimated_duration_minutes: durationHours ? Math.round(Number.parseFloat(durationHours) * 60) : null,
        };
        try {
            if (isEdit && route) {
                return await routesService.update(route.id, payload);
            }
            return await routesService.create(payload);
        } catch (e) {
            const detail = (e as {response?: {data?: {detail?: string}}}).response?.data?.detail;
            toast.error(detail || t('routes.toast.saveFailed'));
            return null;
        }
    };

    const handleSaveAndStay = async () => {
        setSaving(true);
        const r = await handleSaveBasics();
        setSaving(false);
        if (r) {
            toast.success(t('routes.toast.saved'));
            if (!isEdit) {
                // If user came from object page with pre-selected stop — add it now
                const pendingStopId = sessionStorage.getItem('routeFirstStopObjectId');
                if (pendingStopId) {
                    sessionStorage.removeItem('routeFirstStopObjectId');
                    try {
                        const stop = await routesService.addStop(r.id, {cultural_object: Number(pendingStopId)});
                        r.stops = [stop];
                        setStops([stop]);
                    } catch {
                        toast.error(t('routes.toast.stopAddFailed'));
                    }
                    setRoute(r);
                }
                navigate(`/routes/${r.id}/edit`, {replace: true});
            } else {
                navigate('/my-routes');
            }
        }
    };

    const handleSearchObjects = async () => {
        if (search.trim().length < 2) {
            setSearchResults([]);
            return;
        }
        setSearching(true);
        try {
            const res = await objectsService.getAll({search: search.trim()});
            const usedIds = new Set(stops.map(s => s.object_id));
            setSearchResults(res.results.filter(o => !usedIds.has(o.id)).slice(0, 8));
        } catch {
            toast.error(t('routes.toast.searchFailed'));
        } finally {
            setSearching(false);
        }
    };

    const handleAddStop = async (objectId: number) => {
        // Ensure route is created before adding stops
        let currentRoute = route;
        if (!currentRoute) {
            currentRoute = await handleSaveBasics();
            if (!currentRoute) return;
            setRoute(currentRoute);
            navigate(`/routes/${currentRoute.id}/edit`, {replace: true});
        }
        try {
            const newStop = await routesService.addStop(currentRoute.id, {cultural_object: objectId});
            setStops(prev => [...prev, newStop]);
            setSearch('');
            setSearchResults([]);
            toast.success(t('routes.toast.stopAdded'));
        } catch (e) {
            const detail = (e as {response?: {data?: {detail?: string}}}).response?.data?.detail;
            toast.error(detail || t('routes.toast.stopAddFailed'));
        }
    };

    const handleRemoveStop = async (stopId: number) => {
        if (!route) return;
        if (!confirm(t('routes.edit.removeStopConfirm'))) return;
        try {
            await routesService.removeStop(route.id, stopId);
            setStops(prev => prev.filter(s => s.id !== stopId).map((s, i) => ({...s, order: i + 1})));
            toast.success(t('routes.toast.stopRemoved'));
        } catch {
            toast.error(t('routes.toast.stopRemoveFailed'));
        }
    };

    const handleDragEnd = async (event: DragEndEvent) => {
        const {active, over} = event;
        if (!over || active.id === over.id || !route) return;
        const oldIdx = stops.findIndex(s => s.id === active.id);
        const newIdx = stops.findIndex(s => s.id === over.id);
        const reordered = arrayMove(stops, oldIdx, newIdx).map((s, i) => ({...s, order: i + 1}));
        setStops(reordered);
        try {
            await routesService.reorder(route.id, reordered.map(s => ({id: s.id, order: s.order})));
        } catch {
            toast.error(t('routes.toast.reorderFailed'));
        }
    };

    const toggleTag = (tagId: number) => {
        setSelectedTags(prev => prev.includes(tagId) ? prev.filter(x => x !== tagId) : [...prev, tagId]);
    };

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <Link to={isEdit && route ? `/routes/${route.id}` : '/my-routes'}
                      className="text-sm text-amber-700 dark:text-amber-400 hover:underline mb-2 inline-block">
                    {t('routes.edit.back')}
                </Link>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100 mb-4">
                    {isEdit ? t('routes.edit.titleEdit') : t('routes.edit.titleNew')}
                </h1>

                <div className="space-y-4">
                    {/* Title */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                            {t('routes.edit.name')} *
                        </label>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            maxLength={200}
                            className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-400"
                        />
                    </div>

                    {/* Visibility */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-2">
                            {t('routes.edit.visibility')}
                        </label>
                        <div className="grid grid-cols-2 gap-2">
                            <button
                                type="button"
                                onClick={() => setVisibility('private')}
                                className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors cursor-pointer text-left ${
                                    visibility === 'private'
                                        ? 'bg-amber-100 dark:bg-amber-900/40 border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-300'
                                        : 'bg-white dark:bg-stone-800 border-gray-200 dark:border-stone-700 text-gray-600 dark:text-stone-300 hover:border-gray-400 dark:hover:border-stone-500'
                                }`}
                            >
                                {t('routes.visibility.private')}
                                <span className="block text-xs font-normal mt-0.5 opacity-80">
                                    {t('routes.edit.privateHint')}
                                </span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setVisibility('public')}
                                className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors cursor-pointer text-left ${
                                    visibility === 'public'
                                        ? 'bg-amber-100 dark:bg-amber-900/40 border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-300'
                                        : 'bg-white dark:bg-stone-800 border-gray-200 dark:border-stone-700 text-gray-600 dark:text-stone-300 hover:border-gray-400 dark:hover:border-stone-500'
                                }`}
                            >
                                {t('routes.visibility.public')}
                                <span className="block text-xs font-normal mt-0.5 opacity-80">
                                    {t('routes.edit.publicHint')}
                                </span>
                            </button>
                        </div>
                        {isEdit && route?.visibility === 'public' && visibility === 'private' && (
                            <p className="text-xs text-amber-700 dark:text-amber-400 mt-2">
                                {t('routes.edit.warnToPrivate')}
                            </p>
                        )}
                        {isEdit && route?.visibility === 'private' && visibility === 'public' && (
                            <p className="text-xs text-amber-700 dark:text-amber-400 mt-2">
                                {t('routes.edit.warnToPublic')}
                            </p>
                        )}
                    </div>

                    {/* Description */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                            {t('routes.edit.description')} *
                        </label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            maxLength={2000}
                            rows={5}
                            className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
                        />
                        <p className="text-xs text-gray-500 dark:text-stone-400 text-right">{description.length} / 2000</p>
                    </div>

                    {/* Duration */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                            {t('routes.edit.duration')}
                        </label>
                        <input
                            type="number"
                            value={durationHours}
                            onChange={(e) => setDurationHours(e.target.value)}
                            min="0"
                            step="0.5"
                            className="w-32 bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-400"
                        />
                    </div>

                    {/* Tags */}
                    {allTags.length > 0 && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-2">
                                {t('routes.edit.tags')}
                            </label>
                            <div className="flex flex-wrap gap-2">
                                {allTags.map(tag => {
                                    const selected = selectedTags.includes(tag.id);
                                    return (
                                        <button
                                            key={tag.id}
                                            type="button"
                                            onClick={() => toggleTag(tag.id)}
                                            className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm border transition-colors cursor-pointer ${
                                                selected
                                                    ? 'bg-amber-100 dark:bg-amber-900/40 border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-300'
                                                    : 'bg-white dark:bg-stone-800 border-gray-200 dark:border-stone-700 text-gray-600 dark:text-stone-300 hover:border-gray-400 dark:hover:border-stone-500'
                                            }`}
                                        >
                                            {tag.icon} {tag.name}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    <button
                        type="button"
                        onClick={handleSaveAndStay}
                        disabled={saving}
                        className="px-4 py-2 bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50"
                    >
                        {saving ? t('routes.edit.saving') : isEdit ? t('routes.edit.saveBtn') : t('routes.edit.createBtn')}
                    </button>
                </div>

                {/* Stops manager (only after route is saved) */}
                {route && (
                    <div className="mt-8">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-stone-100 mb-3">
                            {t('routes.edit.stopsHeader')} ({stops.length}/50)
                        </h2>

                        {stops.length < 50 && (
                            <div className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-3 mb-4">
                                <p className="text-sm font-medium text-gray-700 dark:text-stone-200 mb-2">
                                    {t('routes.edit.addStopHeader')}
                                </p>
                                <div className="flex gap-2 mb-2">
                                    <input
                                        type="text"
                                        value={search}
                                        onChange={(e) => setSearch(e.target.value)}
                                        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleSearchObjects(); } }}
                                        placeholder={t('routes.edit.objectPlaceholder')}
                                        className="flex-1 bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                                    />
                                    <button
                                        type="button"
                                        onClick={handleSearchObjects}
                                        disabled={searching || search.trim().length < 2}
                                        className="px-3 py-1.5 text-sm bg-amber-500 hover:bg-amber-600 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded cursor-pointer disabled:opacity-50"
                                    >
                                        {searching ? '...' : t('routes.edit.searchBtn')}
                                    </button>
                                </div>
                                {searchResults.length > 0 && (
                                    <div className="space-y-1 max-h-60 overflow-y-auto">
                                        {searchResults.map(obj => (
                                            <button
                                                key={obj.id}
                                                type="button"
                                                onClick={() => handleAddStop(obj.id)}
                                                className="w-full text-left px-3 py-2 text-sm border border-gray-200 dark:border-stone-700 rounded hover:bg-amber-50 dark:hover:bg-stone-700 cursor-pointer"
                                            >
                                                <span className="text-gray-900 dark:text-stone-100 font-medium">{obj.title}</span>
                                                {obj.tags.length > 0 && (
                                                    <span className="ml-2 text-xs text-gray-500 dark:text-stone-400">
                                                        {obj.tags.map(t => t.icon).join(' ')}
                                                    </span>
                                                )}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {stops.length === 0 ? (
                            <p className="text-gray-500 dark:text-stone-400 text-sm">
                                {t('routes.edit.emptyStops')}
                            </p>
                        ) : (
                            <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                                <SortableContext items={stops.map(s => s.id)} strategy={verticalListSortingStrategy}>
                                    <div className="space-y-2">
                                        {stops.map(s => (
                                            <SortableStopItem
                                                key={s.id}
                                                stop={s}
                                                onRemove={() => handleRemoveStop(s.id)}
                                                onNoteSave={async (note) => {
                                                    if (!route) return;
                                                    try {
                                                        const updated = await routesService.updateStop(route.id, s.id, {note});
                                                        setStops(prev => prev.map(x => x.id === s.id ? {...x, note: updated.note} : x));
                                                        toast.success(t('routes.toast.noteSaved'));
                                                    } catch {
                                                        toast.error(t('routes.toast.noteSaveFailed'));
                                                    }
                                                }}
                                                dragHint={t('routes.edit.dragHint')}
                                                archivedHint={t('routes.edit.archivedObjectWarn')}
                                                notePlaceholder={t('routes.edit.notePlaceholder')}
                                                saveLabel={t('routes.edit.noteSaveBtn')}
                                                savingLabel={t('routes.edit.noteSaving')}
                                            />
                                        ))}
                                    </div>
                                </SortableContext>
                            </DndContext>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
