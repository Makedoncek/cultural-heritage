import {useState, useEffect, useCallback, useRef} from 'react';
import {useNavigate} from 'react-router';
import {objectsService} from '../services/objects.service';
import {tagsService} from '../services/tags.service';
import MapView from '../components/Map/MapView';
import type {FlyToTarget} from '../components/Map/MapView';
import TagFilter from '../components/Map/TagFilter';
import TypeFilter from '../components/Map/TypeFilter';
import EventStatusFilter from '../components/Map/EventStatusFilter';
import ErrorBoundary from '../components/Layout/ErrorBoundary';
import type {CulturalObject, Tag} from '../types';

export default function HomePage() {
    const [objects, setObjects] = useState<CulturalObject[]>([]);
    const [tags, setTags] = useState<Tag[]>([]);
    const [selectedTags, setSelectedTags] = useState<number[]>([]);
    const [objectType, setObjectType] = useState('all');
    const [eventStatus, setEventStatus] = useState('all');
    const [search, setSearch] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [searchFocused, setSearchFocused] = useState(false);
    const [flyTo, setFlyTo] = useState<FlyToTarget | null>(null);
    const navigate = useNavigate();
    const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const tagType = objectType === 'all' ? undefined : objectType;
        tagsService.getAll(tagType).then(res => {
            setTags(res.results);
            // Зберігаємо ту саму array-reference коли список і так порожній,
            // інакше useEffect нижче тригериться повторно і дублює fetch.
            setSelectedTags(prev => prev.length === 0 ? prev : []);
        }).catch(() => {});
        setEventStatus(prev => (objectType !== 'event' && prev !== 'all' ? 'all' : prev));
    }, [objectType]);

    useEffect(() => {
        debounceRef.current = setTimeout(() => setDebouncedSearch(search.length >= 3 ? search : ''), 1000);
        return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
    }, [search]);

    const fetchObjects = useCallback(async (
        tagIds: number[],
        searchQuery: string,
        type: string,
        evStatus: string,
        signal: AbortSignal,
    ) => {
        setLoading(true);
        setError(null);

        try {
            const params: Record<string, string | number> = {};
            if (tagIds.length > 0) params.tags = tagIds.join(',');
            if (searchQuery) params.search = searchQuery;
            if (type !== 'all') params.object_type = type;
            if (type === 'event' && evStatus !== 'all') params.event_status = evStatus;

            const first = await objectsService.getAll({...params, page: 1}, signal);
            const pageSize = first.results.length || 100;
            const totalPages = Math.ceil(first.count / pageSize);

            if (totalPages <= 1) {
                setObjects(first.results);
                return;
            }

            const rest = await Promise.all(
                Array.from({length: totalPages - 1}, (_, i) =>
                    objectsService.getAll({...params, page: i + 2}, signal)
                )
            );

            setObjects([...first.results, ...rest.flatMap(r => r.results)]);
        } catch (err) {
            // Скасований запит (StrictMode-double-effect, зміна фільтрів під час loading) — мовчки ігноруємо
            if ((err as {code?: string})?.code === 'ERR_CANCELED') return;
            setError('Не вдалося завантажити культурні об\'єкти.');
        } finally {
            if (!signal.aborted) setLoading(false);
        }
    }, []);

    useEffect(() => {
        const controller = new AbortController();
        fetchObjects(selectedTags, debouncedSearch, objectType, eventStatus, controller.signal);
        return () => controller.abort();
    }, [selectedTags, debouncedSearch, objectType, eventStatus, fetchObjects]);

    const handleTagToggle = (tagId: number) => {
        setSelectedTags(prev =>
            prev.includes(tagId)
                ? prev.filter(id => id !== tagId)
                : [...prev, tagId]
        );
    };

    const handleClearTags = () => setSelectedTags([]);

    if (loading && objects.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
                    <p className="text-gray-600">Завантаження...</p>
                </div>
            </div>
        );
    }

    if (error && objects.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <p className="text-red-600">{error}</p>
                    <button
                        onClick={() => fetchObjects(selectedTags, debouncedSearch, objectType, eventStatus)}
                        className="px-4 py-2 bg-amber-500 text-white rounded hover:bg-amber-600 cursor-pointer"
                    >
                        Спробувати знову
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-1 relative">
            {!sidebarOpen && (
                <button
                    onClick={() => setSidebarOpen(true)}
                    className="md:hidden absolute top-3 right-3 z-[1000] bg-white rounded-lg shadow-md px-3 py-2 text-sm font-medium text-amber-700 border border-amber-200 cursor-pointer"
                >
                    ☰ Фільтри
                </button>
            )}

            <aside
                className={`
                    absolute md:relative z-[1001] bg-white border-r border-gray-200 shadow-lg md:shadow-none
                    w-60 overflow-y-auto flex-shrink-0
                    transition-transform duration-200
                    h-full
                    ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
                    md:translate-x-0
                `}
            >
                <div className="p-4 pt-3">
                    <div className="flex items-center justify-between md:hidden mb-3">
                        <span className="text-sm font-semibold text-gray-700">Фільтри</span>
                        <button
                            onClick={() => setSidebarOpen(false)}
                            className="text-gray-400 hover:text-gray-600 cursor-pointer text-lg leading-none"
                        >
                            ✕
                        </button>
                    </div>

                    <div className="relative mb-4" ref={dropdownRef}>
                        <input
                            type="text"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            onFocus={() => setSearchFocused(true)}
                            onBlur={(e) => {
                                if (!dropdownRef.current?.contains(e.relatedTarget)) {
                                    setSearchFocused(false);
                                }
                            }}
                            placeholder="Пошук за назвою..."
                            className="w-full px-3 py-2 pr-8 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-amber-500"
                        />
                        {search && (
                            <button
                                onClick={() => setSearch('')}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 cursor-pointer"
                            >
                                ✕
                            </button>
                        )}
                        {search.length >= 3 && searchFocused && objects.length > 0 && (
                            <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto z-10">
                                {objects.slice(0, 7).map(obj => (
                                    <div
                                        key={obj.id}
                                className="flex items-center gap-2 px-3 py-2 hover:bg-amber-50 cursor-pointer text-sm border-b border-gray-100 last:border-b-0"
                                        onMouseDown={(e) => e.preventDefault()}
                                        onClick={() => {
                                            setFlyTo({latitude: Number(obj.latitude), longitude: Number(obj.longitude)});
                                            setSearchFocused(false);
                                            setSidebarOpen(false);
                                        }}
                                    >
                                        <span>{obj.tags[0]?.icon || '📍'}</span>
                                        <span className="flex-1 truncate text-gray-700">{obj.title}</span>
                                        <button
                                            onMouseDown={(e) => e.preventDefault()}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                navigate(`/objects/${obj.id}`);
                                            }}
                                            className="text-amber-500 hover:text-amber-700 hover:bg-amber-50 cursor-pointer text-sm flex-shrink-0 px-2 py-1 rounded"
                                            title="Детальніше"
                                        >
                                            ➜
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    <TypeFilter value={objectType} onChange={setObjectType}/>
                    {objectType === 'event' && (
                        <>
                            <hr className="my-3 border-gray-200"/>
                            <EventStatusFilter value={eventStatus} onChange={setEventStatus}/>
                        </>
                    )}
                    <hr className="my-3 border-gray-200"/>
                    <TagFilter
                        tags={tags}
                        selectedTags={selectedTags}
                        onTagToggle={handleTagToggle}
                        onClear={handleClearTags}
                    />
                </div>
            </aside>

            <div className="relative flex-1">
                <ErrorBoundary>
                    <MapView objects={objects} flyTo={flyTo}/>
                </ErrorBoundary>

                {!loading && objects.length > 0 && (
                    <div className="absolute top-3 right-3 z-[400] bg-white/95 backdrop-blur-sm rounded-lg shadow-md px-3 py-2 text-sm border border-gray-200">
                        <div className="flex items-center gap-2">
                            <span className="text-gray-500">На мапі:</span>
                            <span className="font-bold text-gray-900">{objects.length}</span>
                        </div>
                        {(() => {
                            const events = objects.filter(o => o.object_type === 'event').length;
                            const permanent = objects.length - events;
                            if (events === 0 || permanent === 0) return null;
                            return (
                                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                                    <span>Пам'ятки: <span className="text-gray-700 font-medium">{permanent}</span></span>
                                    <span>Події: <span className="text-gray-700 font-medium">{events}</span></span>
                                </div>
                            );
                        })()}
                    </div>
                )}

                {loading && objects.length > 0 && (
                    <div className="absolute inset-0 z-[500] flex items-center justify-center bg-black/10 pointer-events-none">
                        <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
                    </div>
                )}

                {!loading && objects.length === 0 && (
                    <div className="absolute inset-0 z-[500] flex items-center justify-center pointer-events-none">
                        <div className="bg-white/90 rounded-lg px-6 py-4 shadow-md">
                            <p className="text-gray-600">Нічого не знайдено</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
