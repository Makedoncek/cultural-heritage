import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import {routesService} from '../services/routes.service';
import type {RouteListItem} from '../types/routes';

export default function RoutesListPage() {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const [routes, setRoutes] = useState<RouteListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [featuredOnly, setFeaturedOnly] = useState(false);

    useEffect(() => {
        setLoading(true);
        routesService.list({is_featured: featuredOnly || undefined})
            .then(setRoutes)
            .catch(() => setError('Не вдалося завантажити маршрути.'))
            .finally(() => setLoading(false));
    }, [featuredOnly]);

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
                        🗺 Маршрути культурної спадщини
                    </h1>
                    <Link
                        to="/routes/add"
                        className="px-4 py-2 bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 text-sm font-medium rounded-lg"
                    >
                        + Створити маршрут
                    </Link>
                </div>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-4">
                    Кураторські туристичні маршрути культурною спадщиною України з експортом GPX/KML.
                </p>

                <div className="flex items-center gap-3 mb-6">
                    <label className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-stone-200 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={featuredOnly}
                            onChange={(e) => setFeaturedOnly(e.target.checked)}
                            className="w-4 h-4 accent-amber-500 cursor-pointer"
                        />
                        ⭐ Тільки рекомендовані
                    </label>
                    <Link to="/my-routes" className="text-sm text-amber-700 dark:text-amber-400 hover:underline">
                        📋 Мої маршрути →
                    </Link>
                </div>

                {routes.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500 dark:text-stone-400">
                            Поки що немає опублікованих маршрутів. Створи перший!
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
                                {r.cover_photo ? (
                                    <img
                                        src={r.cover_photo}
                                        alt={r.title}
                                        className="w-full h-32 object-cover"
                                    />
                                ) : (
                                    <div className="w-full h-32 bg-gradient-to-br from-amber-100 to-yellow-100 dark:from-stone-800 dark:to-stone-700 flex items-center justify-center text-4xl">
                                        🗺
                                    </div>
                                )}
                                <div className="p-3">
                                    <div className="flex items-start justify-between gap-2 mb-1">
                                        <h2 className="text-base font-semibold text-gray-900 dark:text-stone-100 line-clamp-2">
                                            {r.title}
                                        </h2>
                                        {r.is_featured && (
                                            <span className="text-amber-500 dark:text-amber-400 text-sm shrink-0" title="Рекомендований">⭐</span>
                                        )}
                                    </div>
                                    <p className="text-xs text-gray-500 dark:text-stone-400 mb-2">
                                        @{r.author_name} · {r.stops_count} зупинок
                                        {r.estimated_duration_minutes != null && r.estimated_duration_minutes > 0 && (
                                            <> · ~{Math.round(r.estimated_duration_minutes / 60)} год</>
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
