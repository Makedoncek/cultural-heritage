import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import {routesService} from '../services/routes.service';
import {tagsService} from '../services/tags.service';
import type {RouteListItem} from '../types/routes';
import type {Tag} from '../types';

type DurationBucket = '' | 'short' | 'medium' | 'long';

const DURATION_BUCKETS: Record<DurationBucket, {min?: number; max?: number}> = {
    '': {},
    short: {max: 119},          // <2 год
    medium: {min: 120, max: 300}, // 2-5 год
    long: {min: 301},           // >5 год
};

export default function RoutesListPage() {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const [routes, setRoutes] = useState<RouteListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [featuredOnly, setFeaturedOnly] = useState(false);
    const [search, setSearch] = useState('');
    const [searchInput, setSearchInput] = useState('');
    const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
    const [duration, setDuration] = useState<DurationBucket>('');
    const [allTags, setAllTags] = useState<Tag[]>([]);

    useEffect(() => {
        tagsService.getAll().then(r => setAllTags(r.results)).catch(() => {});
    }, []);

    useEffect(() => {
        setLoading(true);
        const bucket = DURATION_BUCKETS[duration];
        routesService.list({
            is_featured: featuredOnly || undefined,
            tags: selectedTagIds.length ? selectedTagIds : undefined,
            search: search || undefined,
            duration_min: bucket.min,
            duration_max: bucket.max,
        })
            .then(setRoutes)
            .catch(() => setError(t('routes.loadError')))
            .finally(() => setLoading(false));
    }, [featuredOnly, selectedTagIds, search, duration, t]);

    const toggleTag = (id: number) => {
        setSelectedTagIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
    };

    const onSearchSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setSearch(searchInput.trim());
    };

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
                    <p className="text-gray-600 dark:text-stone-300">{t('home.loading')}</p>
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
            <div className="max-w-4xl mx-auto px-4 py-6">
                <div className="flex flex-wrap items-center justify-between mb-2 gap-3">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100">
                        🗺 {t('routes.title')}
                    </h1>
                    <Link
                        to="/routes/add"
                        className="px-4 py-2 bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 text-sm font-medium rounded-lg"
                    >
                        {t('routes.createButton')}
                    </Link>
                </div>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-4">
                    {t('routes.subtitle')}
                </p>

                <div className="space-y-3 mb-6">
                    <form onSubmit={onSearchSubmit} className="flex gap-2">
                        <input
                            type="search"
                            value={searchInput}
                            onChange={(e) => setSearchInput(e.target.value)}
                            placeholder={t('routes.searchPlaceholder')}
                            className="flex-1 bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                        />
                        <button
                            type="submit"
                            className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer"
                        >
                            🔍
                        </button>
                        {search && (
                            <button
                                type="button"
                                onClick={() => { setSearch(''); setSearchInput(''); }}
                                className="px-3 py-2 text-sm border border-gray-300 dark:border-stone-600 text-gray-700 dark:text-stone-200 rounded-lg hover:bg-gray-100 dark:hover:bg-stone-800 cursor-pointer"
                            >
                                ✕
                            </button>
                        )}
                    </form>

                    <div className="flex flex-wrap items-center gap-3">
                        <label className="inline-flex items-center gap-2 text-base text-gray-700 dark:text-stone-200 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={featuredOnly}
                                onChange={(e) => setFeaturedOnly(e.target.checked)}
                                className="w-5 h-5 accent-amber-500 cursor-pointer"
                            />
                            ⭐ {t('routes.featuredOnly')}
                        </label>
                        <select
                            value={duration}
                            onChange={(e) => setDuration(e.target.value as DurationBucket)}
                            className="bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 cursor-pointer"
                        >
                            <option value="">⏱ {t('routes.anyDuration')}</option>
                            <option value="short">{t('routes.durationShort')}</option>
                            <option value="medium">{t('routes.durationMedium')}</option>
                            <option value="long">{t('routes.durationLong')}</option>
                        </select>
                        <Link to="/my-routes" className="text-base text-amber-700 dark:text-amber-400 hover:underline">
                            📋 {t('routes.myRoutes')}
                        </Link>
                    </div>

                    {allTags.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                            {allTags.map(tag => {
                                const selected = selectedTagIds.includes(tag.id);
                                return (
                                    <button
                                        key={tag.id}
                                        type="button"
                                        onClick={() => toggleTag(tag.id)}
                                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border transition-colors cursor-pointer ${
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
                    )}
                </div>

                {routes.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500 dark:text-stone-400">
                            {t('routes.empty')}
                        </p>
                    </div>
                ) : (
                    <div className="grid sm:grid-cols-2 gap-4">
                        {routes.map(r => (
                            <Link
                                key={r.id}
                                to={`/routes/${r.id}`}
                                className="block border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg overflow-hidden hover:border-amber-400 dark:hover:border-amber-500 transition-colors"
                            >
                                <div className="w-full h-32 bg-gradient-to-br from-amber-100 to-yellow-100 dark:from-stone-800 dark:to-stone-700 flex items-center justify-center text-4xl">
                                    🗺
                                </div>
                                <div className="p-3">
                                    <div className="flex items-start justify-between gap-2 mb-1">
                                        <h2 className="text-base font-semibold text-gray-900 dark:text-stone-100 line-clamp-2">
                                            {r.title}
                                        </h2>
                                        {r.is_featured && (
                                            <span className="text-amber-500 dark:text-amber-400 text-sm shrink-0" title={t('routes.featured')}>⭐</span>
                                        )}
                                    </div>
                                    <p className="text-xs text-gray-500 dark:text-stone-400 mb-2">
                                        @{r.author_name} · {r.stops_count} {t('routes.stops')}
                                        {r.estimated_duration_minutes != null && r.estimated_duration_minutes > 0 && (
                                            <> · ~{Math.round(r.estimated_duration_minutes / 60)} {t('routes.hours')}</>
                                        )}
                                    </p>
                                    <p className="text-sm text-gray-700 dark:text-stone-300 line-clamp-2">
                                        {r.description}
                                    </p>
                                    {r.tags.length > 0 && (
                                        <div className="flex flex-wrap gap-1 mt-2">
                                            {r.tags.slice(0, 4).map(tag => (
                                                <span
                                                    key={tag.id}
                                                    className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded text-xs"
                                                >
                                                    {tag.icon} {tag.name}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                    <p className="text-[10px] text-gray-400 dark:text-stone-500 mt-2">
                                        {new Date(r.updated_at).toLocaleDateString(dateLocale)}
                                    </p>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
