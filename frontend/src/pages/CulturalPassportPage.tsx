import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import toast from 'react-hot-toast';
import {visitsService, plannedVisitsService} from '../services/visits.service';
import {routesService} from '../services/routes.service';
import type {Visit, PlannedVisit, VisitsStats} from '../types/visits';
import type {RouteListItem} from '../types/routes';
import VisitImpressionModal from '../components/Objects/VisitImpressionModal';
import LoadMoreButton from '../components/Common/LoadMoreButton';
import PassportMap from '../components/Passport/PassportMap';

export default function CulturalPassportPage() {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const [visits, setVisits] = useState<Visit[]>([]);
    const [planned, setPlanned] = useState<PlannedVisit[]>([]);
    const [stats, setStats] = useState<VisitsStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [editingVisit, setEditingVisit] = useState<Visit | null>(null);

    const [visitsNextUrl, setVisitsNextUrl] = useState<string | null>(null);
    const [visitsTotal, setVisitsTotal] = useState(0);
    const [loadingMoreVisits, setLoadingMoreVisits] = useState(false);

    const [completedRoutes, setCompletedRoutes] = useState<RouteListItem[]>([]);
    const [completedNextUrl, setCompletedNextUrl] = useState<string | null>(null);
    const [completedTotal, setCompletedTotal] = useState(0);
    const [loadingMoreCompleted, setLoadingMoreCompleted] = useState(false);

    useEffect(() => {
        Promise.all([
            visitsService.listMine(),
            plannedVisitsService.listMine(),
            visitsService.stats(),
            routesService.listCompleted(),
        ])
            .then(([v, p, s, cr]) => {
                setVisits(v.results);
                setVisitsNextUrl(v.next);
                setVisitsTotal(v.count);
                setPlanned(p.results);
                setStats(s);
                setCompletedRoutes(cr.results);
                setCompletedNextUrl(cr.next);
                setCompletedTotal(cr.count);
            })
            .catch(() => setError(t('passport.loadError')))
            .finally(() => setLoading(false));
    }, []);

    const loadMoreCompleted = async () => {
        if (!completedNextUrl || loadingMoreCompleted) return;
        setLoadingMoreCompleted(true);
        try {
            const path = completedNextUrl.replace(/^https?:\/\/[^/]+\/api/, '');
            const data = await routesService.listCompletedByUrl(path);
            setCompletedRoutes(prev => [...prev, ...data.results]);
            setCompletedNextUrl(data.next);
        } catch {
            toast.error(t('common.loadMoreError'));
        } finally {
            setLoadingMoreCompleted(false);
        }
    };

    const loadMoreVisits = async () => {
        if (!visitsNextUrl || loadingMoreVisits) return;
        setLoadingMoreVisits(true);
        try {
            const path = visitsNextUrl.replace(/^https?:\/\/[^/]+\/api/, '');
            const data = await visitsService.listMineByUrl(path);
            setVisits(prev => [...prev, ...data.results]);
            setVisitsNextUrl(data.next);
        } catch {
            toast.error(t('common.loadMoreError'));
        } finally {
            setLoadingMoreVisits(false);
        }
    };

    const togglePublic = async (v: Visit) => {
        try {
            const updated = await visitsService.update(v.id, {is_public: !v.is_public});
            setVisits(prev => prev.map(x => x.id === v.id ? updated : x));
            toast.success(updated.is_public ? t('passport.nowPublic') : t('passport.nowPrivate'));
        } catch {
            toast.error(t('passport.updateError'));
        }
    };

    const convertToVisit = async (p: PlannedVisit) => {
        try {
            const result = await plannedVisitsService.convertToVisit(p.id);
            setPlanned(prev => prev.filter(x => x.id !== p.id));
            setVisits(prev => [result.visit, ...prev]);
            toast.success(t('passport.movedToVisited'));
        } catch {
            toast.error(t('passport.convertError'));
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
    if (error) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <p className="text-red-600">{error}</p>
            </div>
        );
    }

    const percent = stats && stats.total_approved_objects > 0
        ? (stats.total_visits / stats.total_approved_objects * 100).toFixed(2)
        : '0';

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100 mb-2">
                    🎒 {t('passport.title')}
                </h1>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-6">
                    {t('passport.subtitle')}
                </p>

                {/* Counters */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
                    <div className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-4">
                        <p className="text-xs text-gray-500 dark:text-stone-400 uppercase tracking-wide">📊 {t('passport.statVisited')}</p>
                        <p className="text-3xl font-bold text-amber-700 dark:text-amber-400 mt-1">
                            {stats?.total_visits ?? 0}
                            <span className="text-base text-gray-500 dark:text-stone-400 font-normal ml-1">
                                {t('passport.statVisitedOf', {total: stats?.total_approved_objects ?? 0, percent})}
                            </span>
                        </p>
                    </div>
                    <div className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-4">
                        <p className="text-xs text-gray-500 dark:text-stone-400 uppercase tracking-wide">📌 {t('passport.statPlanned')}</p>
                        <p className="text-3xl font-bold text-blue-700 dark:text-blue-400 mt-1">
                            {planned.length}
                        </p>
                    </div>
                    <div className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-4">
                        <p className="text-xs text-gray-500 dark:text-stone-400 uppercase tracking-wide">🏆 {t('passport.statRoutesCompleted')}</p>
                        <p className="text-3xl font-bold text-green-700 dark:text-green-400 mt-1">
                            {stats?.completed_routes ?? 0}
                        </p>
                    </div>
                </div>

                {/* By tag */}
                {stats && stats.by_tag.length > 0 && (
                    <div className="mb-6 border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-4">
                        <h2 className="text-sm font-semibold text-gray-700 dark:text-stone-200 uppercase tracking-wide mb-2">
                            {t('passport.byTag')}
                        </h2>
                        <div className="flex flex-wrap gap-2">
                            {stats.by_tag.map(tag => (
                                <span
                                    key={tag.id}
                                    className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded-full text-sm"
                                >
                                    {tag.icon} {tag.name}
                                    <strong className="ml-1">{tag.visited_count}</strong>
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                <PassportMap visits={visits} planned={planned}/>

                {/* Visits list */}
                <h2 className="text-lg font-semibold text-gray-900 dark:text-stone-100 mb-3">
                    📋 {t('passport.visitsTimeline')} ({visits.length})
                </h2>
                {visits.length === 0 ? (
                    <p className="text-gray-500 dark:text-stone-400 text-sm mb-6">
                        {t('passport.visitsEmpty')}
                    </p>
                ) : (
                    <div className="space-y-2 mb-6">
                        {visits.map(v => (
                            <div
                                key={v.id}
                                className="flex items-center justify-between gap-2 border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                            >
                                <div className="flex-1 min-w-0">
                                    <Link to={`/objects/${v.object_id}`}
                                          className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300">
                                        {v.object_title}
                                    </Link>
                                    <p className="text-xs text-gray-500 dark:text-stone-400 mt-1">
                                        {new Date(v.visited_at).toLocaleString(dateLocale, {dateStyle: 'short', timeStyle: 'short'})}
                                        {v.impression && (
                                            <span className="ml-2 italic">«{v.impression}»</span>
                                        )}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                    <button
                                        onClick={() => setEditingVisit(v)}
                                        className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400 text-white rounded-lg cursor-pointer"
                                        title={t('passport.editVisitTitle')}
                                    >
                                        {t('object.edit')}
                                    </button>
                                    <button
                                        onClick={() => togglePublic(v)}
                                        className="text-lg cursor-pointer"
                                        title={v.is_public ? t('passport.tooltipMakePrivate') : t('passport.tooltipMakePublic')}
                                    >
                                        {v.is_public ? '🌐' : '🔒'}
                                    </button>
                                </div>
                            </div>
                        ))}
                        <LoadMoreButton
                            show={!!visitsNextUrl}
                            loading={loadingMoreVisits}
                            shown={visits.length}
                            total={visitsTotal}
                            onClick={loadMoreVisits}
                        />
                    </div>
                )}

                {/* Planned list */}
                <h2 className="text-lg font-semibold text-gray-900 dark:text-stone-100 mb-3">
                    📌 {t('passport.plansTitle')} ({planned.length})
                </h2>
                {planned.length === 0 ? (
                    <p className="text-gray-500 dark:text-stone-400 text-sm">
                        {t('passport.plansEmpty')}
                    </p>
                ) : (
                    <div className="space-y-2">
                        {planned.map(p => (
                            <div
                                key={p.id}
                                className="flex items-center justify-between gap-2 border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                            >
                                <div className="flex-1 min-w-0">
                                    <Link to={`/objects/${p.object_id}`}
                                          className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300">
                                        {p.object_title}
                                    </Link>
                                    {p.planned_date && (
                                        <p className="text-xs text-gray-500 dark:text-stone-400 mt-1">
                                            {t('passport.plannedFor', {date: new Date(p.planned_date).toLocaleDateString(dateLocale)})}
                                        </p>
                                    )}
                                </div>
                                <button
                                    onClick={() => convertToVisit(p)}
                                    className="px-3 py-1.5 text-xs bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-300 border border-green-300 dark:border-green-700 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/60 cursor-pointer"
                                >
                                    ✓ {t('passport.markVisited')}
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {/* Completed routes */}
                <h2 className="text-lg font-semibold text-gray-900 dark:text-stone-100 mt-6 mb-3">
                    🏆 {t('passport.completedRoutesTitle')} ({completedTotal})
                </h2>
                {completedRoutes.length === 0 ? (
                    <p className="text-gray-500 dark:text-stone-400 text-sm">
                        {t('passport.completedRoutesEmpty')}
                    </p>
                ) : (
                    <div className="space-y-2">
                        {completedRoutes.map(r => (
                            <div
                                key={r.id}
                                className="flex items-center justify-between gap-2 border border-green-200 dark:border-green-800 bg-green-50/40 dark:bg-green-900/10 rounded-lg px-4 py-3"
                            >
                                <div className="flex-1 min-w-0">
                                    <Link to={`/routes/${r.id}`}
                                          className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300">
                                        {r.title}
                                    </Link>
                                    <p className="text-xs text-gray-500 dark:text-stone-400 mt-1">
                                        {t('passport.completedRoutesStops', {count: r.stops_count})}
                                        <span className="mx-2">·</span>
                                        {t('passport.completedBy', {author: r.author_name})}
                                    </p>
                                </div>
                                <span className="shrink-0 px-2.5 py-1 text-xs rounded-full bg-green-600 dark:bg-green-500 text-white font-semibold">
                                    ✓ {t('passport.completedBadge')}
                                </span>
                            </div>
                        ))}
                        <LoadMoreButton
                            show={!!completedNextUrl}
                            loading={loadingMoreCompleted}
                            shown={completedRoutes.length}
                            total={completedTotal}
                            onClick={loadMoreCompleted}
                        />
                    </div>
                )}
            </div>

            {editingVisit && (
                <VisitImpressionModal
                    visit={editingVisit}
                    onClose={() => setEditingVisit(null)}
                    onUpdated={(u) => setVisits(prev => prev.map(x => x.id === u.id ? u : x))}
                />
            )}
        </div>
    );
}
