import {useState} from 'react';
import {Link} from 'react-router';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {objectsService} from '../services/objects.service';
import {usePaginatedList} from '../hooks/usePaginatedList';
import LoadMoreButton from '../components/Common/LoadMoreButton';
import type {CulturalObject} from '../types';

const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    approved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    archived: 'bg-gray-100 text-gray-600 dark:bg-stone-800 dark:text-stone-400',
};

export default function MyObjectsPage() {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const {items: objects, setItems: setObjects, count: totalCount, nextUrl, loading, loadingMore, loadMore, error} = usePaginatedList<CulturalObject>({
        initialFetch: () => objectsService.getMy(),
        fetchByUrl: (url) => objectsService.getMyByUrl(url),
        onError: () => toast.error(t('common.loadMoreError')),
        deps: [],
    });
    const [deletingId, setDeletingId] = useState<number | null>(null);

    const handleDelete = async (id: number) => {
        if (!confirm(t('object.deleteConfirm'))) return;
        setDeletingId(id);
        try {
            await objectsService.delete(id);
            setObjects(prev => prev.map(obj => obj.id === id ? {...obj, status: 'archived'} : obj));
            toast.success(t('object.archived'));
        } catch {
            toast.error(t('object.deleteError'));
        } finally {
            setDeletingId(null);
        }
    };

    const handleRestore = async (id: number) => {
        setDeletingId(id);
        try {
            await objectsService.restore(id);
            setObjects(prev => prev.map(obj => obj.id === id ? {...obj, status: 'pending'} : obj));
            toast.success('Об\'єкт відновлено');
        } catch {
            toast.error('Не вдалося відновити');
        } finally {
            setDeletingId(null);
        }
    };

    const handleHardDelete = async (id: number) => {
        if (!confirm('Видалити назавжди? Цю дію не можна скасувати.')) return;
        setDeletingId(id);
        try {
            await objectsService.hardDelete(id);
            setObjects(prev => prev.filter(obj => obj.id !== id));
            toast.success('Видалено назавжди');
        } catch {
            toast.error('Не вдалося видалити');
        } finally {
            setDeletingId(null);
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

    if (error && objects.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <p className="text-red-600">{t('home.loadError')}</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <div className="flex items-center justify-between mb-2">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100">{t('myObjects.title')}</h1>
                    <Link
                        to="/objects/add"
                        className="px-4 py-2 bg-amber-600 dark:bg-amber-500 hover:bg-amber-700 dark:hover:bg-amber-400 text-white dark:text-stone-900 text-sm rounded-lg"
                    >
                        {t('myObjects.addNew')}
                    </Link>
                </div>
                <div className="flex flex-wrap gap-2 mb-6">
                    <Link
                        to="/passport"
                        className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-amber-300 dark:border-stone-600 bg-amber-50 dark:bg-stone-800 text-amber-800 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-stone-700 hover:border-amber-400 dark:hover:border-amber-500 transition-colors"
                    >
                        <span className="text-base">🎒</span>
                        Паспорт мандрівника
                    </Link>
                    <Link
                        to="/reports"
                        className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-amber-300 dark:border-stone-600 bg-amber-50 dark:bg-stone-800 text-amber-800 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-stone-700 hover:border-amber-400 dark:hover:border-amber-500 transition-colors"
                    >
                        <span className="text-base">⚠</span>
                        {t('reports.title')}
                    </Link>
                </div>

                {objects.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500 dark:text-stone-400 mb-4">{t('myObjects.empty')}</p>
                        <Link
                            to="/objects/add"
                            className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 underline"
                        >
                            {t('myObjects.addFirst')}
                        </Link>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {objects.map(obj => (
                            <div
                                key={obj.id}
                                className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                            >
                                <div className="min-w-0">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <Link
                                            to={`/objects/${obj.id}`}
                                            className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300"
                                        >
                                            {obj.title}
                                        </Link>
                                        <span className={`px-2.5 py-0.5 text-xs font-medium rounded ${STATUS_COLORS[obj.status]}`}>
                                            {t(`object.moderationStatus.${obj.status}`)}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-stone-400 mt-1">
                                        {obj.tags.length > 0 && (
                                            <span>{obj.tags.map(t => t.icon).join(' ')}</span>
                                        )}
                                        <span>{new Date(obj.created_at).toLocaleDateString(dateLocale)}</span>
                                    </div>
                                </div>
                                <div className="flex gap-2 flex-wrap shrink-0">
                                    {obj.status === 'archived' ? (
                                        <>
                                            <button
                                                onClick={() => handleRestore(obj.id)}
                                                disabled={deletingId === obj.id}
                                                className="px-3 py-1.5 text-sm bg-amber-500 hover:bg-amber-600 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50"
                                            >
                                                ↩ Відновити
                                            </button>
                                            <button
                                                onClick={() => handleHardDelete(obj.id)}
                                                disabled={deletingId === obj.id}
                                                className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg cursor-pointer disabled:opacity-50"
                                            >
                                                🗑 Видалити назавжди
                                            </button>
                                        </>
                                    ) : (
                                        <>
                                            <Link
                                                to={`/objects/${obj.id}`}
                                                className="px-3 py-1.5 text-sm bg-amber-500 hover:bg-amber-600 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg"
                                            >
                                                {t('myObjects.view')}
                                            </Link>
                                            <Link
                                                to={`/objects/${obj.id}/edit`}
                                                className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400 text-white rounded-lg"
                                            >
                                                {t('object.edit')}
                                            </Link>
                                            <button
                                                onClick={() => handleDelete(obj.id)}
                                                disabled={deletingId === obj.id}
                                                className="px-3 py-1.5 text-sm bg-stone-200 hover:bg-stone-300 dark:bg-stone-700 dark:hover:bg-stone-600 text-stone-700 dark:text-stone-200 rounded-lg cursor-pointer disabled:opacity-50"
                                            >
                                                {deletingId === obj.id ? t('object.deleting') : `📦 ${t('object.delete')}`}
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}
                        <LoadMoreButton
                            show={!!nextUrl}
                            loading={loadingMore}
                            shown={objects.length}
                            total={totalCount}
                            onClick={loadMore}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}
