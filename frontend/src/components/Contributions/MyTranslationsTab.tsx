import {Link} from 'react-router';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {translationsService} from '../../services/translations.service';
import {usePaginatedList} from '../../hooks/usePaginatedList';
import LoadMoreButton from '../common/LoadMoreButton';
import type {MyTranslation, TranslationStatus} from '../../types/translations';

const LANG_LABEL: Record<string, string> = {uk: 'UA', en: 'EN', pl: 'PL', de: 'DE'};

const STATUS_CLS: Record<TranslationStatus, string> = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    approved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    rejected: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
};

export default function MyTranslationsTab() {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const {items, count: totalCount, nextUrl, loading, loadingMore, loadMore, error} = usePaginatedList<MyTranslation>({
        initialFetch: () => translationsService.listMine(),
        fetchByUrl: (url) => translationsService.listMineByUrl(url),
        onError: () => toast.error(t('common.loadMoreError')),
        deps: [],
    });

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
            </div>
        );
    }
    if (error && items.length === 0) {
        return <p className="text-red-600 text-center py-6">{t('myPhotos.loadError')}</p>;
    }
    if (items.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500 dark:text-stone-400 mb-4">{t('contributions.translationsEmpty')}</p>
                <Link to="/" className="text-amber-600 dark:text-amber-400 hover:underline">
                    {t('myPhotos.goToMap')}
                </Link>
            </div>
        );
    }

    return (
        <>
            <div className="space-y-2">
                {items.map(tr => (
                    <div
                        key={`${tr.kind}-${tr.id}`}
                        className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                    >
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                            <div className="flex items-center gap-2 min-w-0">
                                <span className="px-2 py-0.5 text-xs rounded-full bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-300">
                                    {tr.kind === 'route' ? t('contributions.kindRoute') : t('contributions.kindObject')}
                                </span>
                                <span className="px-2 py-0.5 text-xs rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 font-semibold">
                                    {LANG_LABEL[tr.language] ?? tr.language}
                                </span>
                                <Link
                                    to={tr.target_url}
                                    className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300 truncate"
                                >
                                    {tr.target_title}
                                </Link>
                            </div>
                            <span className={`px-2 py-0.5 text-xs rounded-full font-medium shrink-0 ${STATUS_CLS[tr.status]}`}>
                                {t(`contributions.translationStatus.${tr.status}`)}
                            </span>
                        </div>
                        <p className="text-sm text-gray-700 dark:text-stone-300 mt-2 truncate">
                            {tr.title}
                        </p>
                        {tr.status === 'rejected' && tr.reviewer_note && (
                            <p className="text-xs text-red-700 dark:text-red-300 mt-1">
                                {t('contributions.reviewerNote')}: {tr.reviewer_note}
                            </p>
                        )}
                        <p className="text-xs text-gray-400 dark:text-stone-500 mt-1">
                            {new Date(tr.created_at).toLocaleDateString(dateLocale)}
                        </p>
                    </div>
                ))}
            </div>
            <LoadMoreButton
                show={!!nextUrl}
                loading={loadingMore}
                shown={items.length}
                total={totalCount}
                onClick={loadMore}
            />
        </>
    );
}
