import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {visitsService} from '../../services/visits.service';
import {usePaginatedList} from '../../hooks/usePaginatedList';
import LoadMoreButton from '../Common/LoadMoreButton';
import PassportMap from '../Passport/PassportMap';
import type {Visit, VisitMapPoint} from '../../types/visits';

interface Props {
    username: string;
    onCountChange?: (count: number) => void;
}

export default function AuthorVisitsTab({username, onCountChange}: Readonly<Props>) {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const {items: visits, count: totalCount, nextUrl, loading, loadingMore, loadMore, error} = usePaginatedList<Visit>({
        initialFetch: () => visitsService.listPublic(username),
        fetchByUrl: (url) => visitsService.listPublicByUrl(url),
        onError: () => toast.error(t('common.loadMoreError')),
        deps: [username],
    });

    const [mapVisits, setMapVisits] = useState<VisitMapPoint[]>([]);

    useEffect(() => { onCountChange?.(totalCount); }, [totalCount, onCountChange]);

    // The map shows ALL public visits, independent of the paginated list below.
    useEffect(() => {
        visitsService.listPublicMap(username).then(setMapVisits).catch(() => {});
    }, [username]);

    if (loading) return <div className="flex justify-center py-8"><div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/></div>;
    if (error && visits.length === 0) return <p className="text-red-600 text-center py-6">{t('authorVisits.loadError')}</p>;
    if (visits.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500 dark:text-stone-400">{t('authorVisits.empty')}</p>
            </div>
        );
    }

    return (
        <>
            <p className="text-sm text-gray-700 dark:text-stone-200 mb-3">
                {t('authorVisits.publicCount')} <strong className="text-amber-700 dark:text-amber-400">{visits.length}</strong>
            </p>
            {mapVisits.length > 0 && (
                <PassportMap visits={mapVisits} planned={[]} subtitleKey="passport.mapSubtitleAuthor"/>
            )}
            <div className="space-y-2">
                {visits.map(v => (
                    <div key={v.id} className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3">
                        <Link to={`/objects/${v.object_id}`} className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300">
                            {v.object_title}
                        </Link>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-stone-400">
                            {v.object_tags.length > 0 && (
                                <span>{v.object_tags.map(tag => tag.icon).join(' ')}</span>
                            )}
                            <span>
                                {new Date(v.visited_at).toLocaleString(dateLocale, {dateStyle: 'short', timeStyle: 'short'})}
                            </span>
                        </div>
                        {v.impression && (
                            <p className="text-sm text-gray-700 dark:text-stone-200 italic mt-2">
                                «{v.impression}»
                            </p>
                        )}
                    </div>
                ))}
            </div>
            <LoadMoreButton
                show={!!nextUrl}
                loading={loadingMore}
                shown={visits.length}
                total={totalCount}
                onClick={loadMore}
            />
        </>
    );
}
