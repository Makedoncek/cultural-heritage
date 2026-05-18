import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import {routesService} from '../services/routes.service';
import type {RouteListItem, RouteStatus} from '../types/routes';

const STATUS_BADGE: Record<RouteStatus, string> = {
    draft: 'bg-gray-100 text-gray-700 dark:bg-stone-800 dark:text-stone-300',
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    approved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    archived: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
};

const STATUS_LABEL: Record<RouteStatus, string> = {
    draft: 'Чернетка',
    pending: 'На модерації',
    approved: 'Опубліковано',
    archived: 'Архів',
};

const VISIBILITY_BADGE = {
    private: 'bg-gray-100 text-gray-700 dark:bg-stone-800 dark:text-stone-300',
    public: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
} as const;

const VISIBILITY_LABEL = {
    private: '🔒 Особистий',
    public: '🌐 Публічний',
} as const;

export default function MyRoutesPage() {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const [routes, setRoutes] = useState<RouteListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        routesService.listMine()
            .then(setRoutes)
            .catch(() => setError('Не вдалося завантажити маршрути.'))
            .finally(() => setLoading(false));
    }, []);

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
            <div className="max-w-2xl mx-auto px-4 py-6">
                <div className="flex items-center justify-between mb-6">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100">
                        Мої маршрути
                    </h1>
                    <Link
                        to="/routes/add"
                        className="px-4 py-2 bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 text-sm font-medium rounded-lg"
                    >
                        + Створити
                    </Link>
                </div>

                {routes.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500 dark:text-stone-400 mb-4">
                            У вас ще немає маршрутів
                        </p>
                        <Link to="/routes/add" className="text-amber-600 dark:text-amber-400 hover:underline">
                            Створити перший маршрут
                        </Link>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {routes.map(r => (
                            <div
                                key={r.id}
                                className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                            >
                                <div className="flex items-start justify-between gap-2 mb-1">
                                    <Link
                                        to={`/routes/${r.id}`}
                                        className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300 flex-1 min-w-0"
                                    >
                                        {r.title}
                                    </Link>
                                    <div className="flex gap-1 shrink-0">
                                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${VISIBILITY_BADGE[r.visibility]}`}>
                                            {VISIBILITY_LABEL[r.visibility]}
                                        </span>
                                        {r.visibility === 'public' && (
                                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${STATUS_BADGE[r.status]}`}>
                                                {STATUS_LABEL[r.status]}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <p className="text-xs text-gray-500 dark:text-stone-400">
                                    {r.stops_count} зупинок · оновлено {new Date(r.updated_at).toLocaleDateString(dateLocale)}
                                </p>
                                <div className="flex gap-2 mt-2 text-xs">
                                    <Link
                                        to={`/routes/${r.id}/edit`}
                                        className="text-amber-700 dark:text-amber-400 hover:underline"
                                    >
                                        Редагувати
                                    </Link>
                                    <Link
                                        to={`/routes/${r.id}`}
                                        className="text-amber-700 dark:text-amber-400 hover:underline"
                                    >
                                        Переглянути
                                    </Link>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
