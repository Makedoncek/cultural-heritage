import {useState} from 'react';
import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import toast from 'react-hot-toast';
import {routesService} from '../services/routes.service';
import {usePaginatedList} from '../hooks/usePaginatedList';
import LoadMoreButton from '../components/common/LoadMoreButton';
import type {RouteListItem, RouteStatus} from '../types/routes';

const STATUS_BADGE: Record<RouteStatus, string> = {
    draft: 'bg-gray-100 text-gray-700 dark:bg-stone-800 dark:text-stone-300',
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    approved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    archived: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
};

const VISIBILITY_BADGE = {
    private: 'bg-gray-100 text-gray-700 dark:bg-stone-800 dark:text-stone-300',
    public: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
} as const;

export default function MyRoutesPage() {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const {items: routes, setItems: setRoutes, count: totalCount, nextUrl, loading, loadingMore, loadMore, error} = usePaginatedList<RouteListItem>({
        initialFetch: () => routesService.listMine(),
        fetchByUrl: (url) => routesService.listMineByUrl(url),
        onError: () => toast.error(t('common.loadMoreError')),
        deps: [],
    });
    const [actionId, setActionId] = useState<number | null>(null);

    const handleRestore = async (id: number) => {
        setActionId(id);
        try {
            const updated = await routesService.restore(id);
            setRoutes(prev => prev.map(r => r.id === id ? {...r, status: updated.status} : r));
            toast.success(t('routes.toast.restored'));
        } catch {
            toast.error(t('routes.toast.restoreFailed'));
        } finally {
            setActionId(null);
        }
    };

    const handleHardDelete = async (id: number) => {
        if (!confirm(t('routes.confirm.hardDelete'))) return;
        setActionId(id);
        try {
            await routesService.hardDelete(id);
            setRoutes(prev => prev.filter(r => r.id !== id));
            toast.success(t('routes.toast.hardDeleted'));
        } catch {
            toast.error(t('routes.toast.hardDeleteFailed'));
        } finally {
            setActionId(null);
        }
    };

    const handleArchive = async (id: number) => {
        if (!confirm(t('routes.confirm.archive'))) return;
        setActionId(id);
        try {
            await routesService.archive(id);
            setRoutes(prev => prev.map(r => r.id === id ? {...r, status: 'archived'} : r));
            toast.success(t('routes.toast.archived'));
        } catch {
            toast.error(t('routes.toast.archiveFailed'));
        } finally {
            setActionId(null);
        }
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
    if (error && routes.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <p className="text-red-600">{t('routes.loadError')}</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <div className="flex items-center justify-between mb-6">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100">
                        {t('routes.myRoutesTitle')}
                    </h1>
                    <Link
                        to="/routes/add"
                        className="px-4 py-2 bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 text-sm font-medium rounded-lg"
                    >
                        {t('routes.createShort')}
                    </Link>
                </div>

                {routes.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500 dark:text-stone-400 mb-4">
                            {t('routes.emptyMine')}
                        </p>
                        <Link to="/routes/add" className="text-amber-600 dark:text-amber-400 hover:underline">
                            {t('routes.createFirst')}
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
                                            {t(`routes.visibility.${r.visibility}`)}
                                        </span>
                                        {r.visibility === 'public' && (
                                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${STATUS_BADGE[r.status]}`}>
                                                {t(`routes.status.${r.status}`)}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <p className="text-xs text-gray-500 dark:text-stone-400">
                                    {r.stops_count} {t('routes.stops')} · {new Date(r.updated_at).toLocaleDateString(dateLocale)}
                                </p>
                                <div className="flex gap-2 mt-3 flex-wrap">
                                    {r.status === 'archived' ? (
                                        <>
                                            <button
                                                onClick={() => handleRestore(r.id)}
                                                disabled={actionId === r.id}
                                                className="px-3 py-1.5 text-sm bg-amber-500 hover:bg-amber-600 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50"
                                            >
                                                {t('routes.actions.restore')}
                                            </button>
                                            <button
                                                onClick={() => handleHardDelete(r.id)}
                                                disabled={actionId === r.id}
                                                className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg cursor-pointer disabled:opacity-50"
                                            >
                                                {t('routes.actions.hardDelete')}
                                            </button>
                                        </>
                                    ) : (
                                        <>
                                            <Link
                                                to={`/routes/${r.id}`}
                                                className="px-3 py-1.5 text-sm bg-amber-500 hover:bg-amber-600 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg"
                                            >
                                                {t('routes.actions.view')}
                                            </Link>
                                            <Link
                                                to={`/routes/${r.id}/edit`}
                                                className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400 text-white rounded-lg"
                                            >
                                                {t('routes.actions.edit')}
                                            </Link>
                                            <button
                                                onClick={() => handleArchive(r.id)}
                                                disabled={actionId === r.id}
                                                className="px-3 py-1.5 text-sm bg-stone-200 hover:bg-stone-300 dark:bg-stone-700 dark:hover:bg-stone-600 text-stone-700 dark:text-stone-200 rounded-lg cursor-pointer disabled:opacity-50"
                                            >
                                                {t('routes.actions.archive')}
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}
                        <LoadMoreButton
                            show={!!nextUrl}
                            loading={loadingMore}
                            shown={routes.length}
                            total={totalCount}
                            onClick={loadMore}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}
