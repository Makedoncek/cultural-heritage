import {useEffect, useState} from 'react';
import {Link, useParams, useNavigate} from 'react-router';
import {MapContainer, Marker, Polyline, Popup, useMap} from 'react-leaflet';
import L from 'leaflet';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import ThemedTileLayer from '../components/Map/ThemedTileLayer';
import {routesService} from '../services/routes.service';
import {visitsService} from '../services/visits.service';
import {useAuth} from '../context/AuthContext';
import type {RouteDetail} from '../types/routes';
import '../utils/leaflet-fix';

function numberedIcon(n: number, color = '#d97706'): L.DivIcon {
    return L.divIcon({
        html: `<div style="background:${color};color:#fff;border:2px solid #fff;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;box-shadow:0 2px 4px rgba(0,0,0,0.4);">${n}</div>`,
        className: 'route-stop-marker',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
}

function FitToStops({coords}: {coords: [number, number][]}) {
    const map = useMap();
    useEffect(() => {
        if (coords.length === 0) return;
        if (coords.length === 1) {
            map.setView(coords[0], 14);
        } else {
            map.fitBounds(coords, {padding: [40, 40]});
        }
    }, [coords, map]);
    return null;
}

export default function RouteDetailPage() {
    const {id} = useParams<{id: string}>();
    const routeId = id ? Number(id) : null;
    const navigate = useNavigate();
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const {user, isAuthenticated} = useAuth();
    const [route, setRoute] = useState<RouteDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [actionLoading, setActionLoading] = useState(false);

    const isOwner = user && route && user.username === route.author_name;
    const canEdit = isOwner || user?.is_staff;
    const [togglingStopId, setTogglingStopId] = useState<number | null>(null);

    const visitedCount = route?.stops.filter(s => s.is_visited).length ?? 0;
    const totalCount = route?.stops.length ?? 0;
    const progressPct = totalCount > 0 ? Math.round((visitedCount / totalCount) * 100) : 0;

    const allVisited = totalCount > 0 && visitedCount === totalCount;

    const handleMarkRouteCompleted = async () => {
        if (!route) return;
        if (!confirm(t('routes.detail.markRouteCompletedConfirm'))) return;
        setActionLoading(true);
        try {
            await routesService.markCompleted(route.id);
            setRoute(prev => prev ? {
                ...prev,
                stops: prev.stops.map(s => ({...s, is_visited: true})),
            } : prev);
            toast.success(t('routes.toast.routeCompleted'));
        } catch {
            toast.error(t('routes.toast.routeCompletedFailed'));
        } finally {
            setActionLoading(false);
        }
    };

    const handleToggleVisit = async (stopId: number, objectId: number) => {
        setTogglingStopId(stopId);
        try {
            const {is_visited} = await visitsService.toggle(objectId);
            setRoute(prev => prev ? {
                ...prev,
                stops: prev.stops.map(s => s.id === stopId ? {...s, is_visited} : s),
            } : prev);
        } catch {
            toast.error(t('routes.toast.visitFailed'));
        } finally {
            setTogglingStopId(null);
        }
    };

    useEffect(() => {
        if (routeId == null) return;
        routesService.detail(routeId)
            .then(setRoute)
            .catch(() => setError(t('routes.toast.loadFailed')))
            .finally(() => setLoading(false));
    }, [routeId, t]);

    const handleSubmit = async () => {
        if (!route) return;
        if (route.stops_count < 2) {
            toast.error(t('routes.toast.submitMinStops'));
            return;
        }
        setActionLoading(true);
        try {
            const updated = await routesService.submit(route.id);
            setRoute(updated);
            toast.success(t('routes.toast.submitted'));
        } catch (e) {
            const detail = (e as {response?: {data?: {detail?: string}}}).response?.data?.detail;
            toast.error(detail || t('routes.toast.submitFailed'));
        } finally {
            setActionLoading(false);
        }
    };

    const handleCopy = async () => {
        if (!route) return;
        setActionLoading(true);
        try {
            const copy = await routesService.copy(route.id);
            toast.success(t('routes.toast.copied'));
            navigate(`/routes/${copy.id}/edit`);
        } catch {
            toast.error(t('routes.toast.copyFailed'));
        } finally {
            setActionLoading(false);
        }
    };

    const handleArchive = async () => {
        if (!route) return;
        if (!confirm(t('routes.detail.archiveConfirm'))) return;
        setActionLoading(true);
        try {
            await routesService.archive(route.id);
            toast.success(t('routes.toast.archived'));
            navigate('/my-routes');
        } catch {
            toast.error(t('routes.toast.archiveFailed'));
        } finally {
            setActionLoading(false);
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
    if (error || !route) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <p className="text-red-600">{error ?? t('routes.detail.notFound')}</p>
            </div>
        );
    }

    const coords: [number, number][] = route.stops.map(s => [parseFloat(s.latitude), parseFloat(s.longitude)]);

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto px-4 py-6">
                <Link to="/routes" className="text-sm text-amber-700 dark:text-amber-400 hover:underline mb-2 inline-block">
                    {t('routes.detail.back')}
                </Link>

                <div className="flex items-start justify-between flex-wrap gap-2 mb-2">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100">
                        🗺 {route.title}
                    </h1>
                    <div className="flex gap-2">
                        <span className={`px-3 py-1.5 text-base font-medium rounded-lg ${
                            route.visibility === 'public'
                                ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300'
                                : 'bg-gray-100 dark:bg-stone-800 text-gray-700 dark:text-stone-300'
                        }`}>
                            {t(`routes.visibility.${route.visibility}`)}
                        </span>
                        {route.visibility === 'public' && route.status !== 'approved' && (
                            <span className="px-3 py-1.5 text-base font-medium rounded-lg bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-300">
                                {t(`routes.status.${route.status}`)}
                            </span>
                        )}
                    </div>
                </div>

                <p className="text-sm text-gray-500 dark:text-stone-400 mb-3">
                    <Link to={`/authors/${route.author_name}`} className="hover:text-amber-700 dark:hover:text-amber-300">
                        @{route.author_name}
                    </Link>
                    {' · '}{route.stops_count} {t('routes.stops')}
                    {route.estimated_duration_minutes != null && route.estimated_duration_minutes > 0 && (
                        <> · ~{Math.round(route.estimated_duration_minutes / 60)} {t('routes.hours')}</>
                    )}
                    {' · '}{new Date(route.updated_at).toLocaleDateString(dateLocale)}
                </p>

                {route.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                        {route.tags.map(tag => (
                            <span
                                key={tag.id}
                                className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded-full text-sm"
                            >
                                {tag.icon} {tag.name}
                            </span>
                        ))}
                    </div>
                )}

                {/* Action buttons */}
                <div className="flex flex-wrap gap-2 mb-4">
                    {isAuthenticated && route.status === 'approved' && !isOwner && (
                        <button
                            onClick={handleCopy}
                            disabled={actionLoading}
                            className="px-3 py-1.5 text-sm bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 rounded-lg hover:bg-amber-200 dark:hover:bg-amber-900/60 cursor-pointer disabled:opacity-50"
                        >
                            {t('routes.detail.copyBtn')}
                        </button>
                    )}
                    {isOwner && route.visibility === 'public' && route.status === 'draft' && (
                        <button
                            onClick={handleSubmit}
                            disabled={actionLoading}
                            className="px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50"
                            title={route.stops_count < 2 ? t('routes.toast.submitMinStops') : ''}
                        >
                            {t('routes.detail.submitBtn')}
                        </button>
                    )}
                    {canEdit && (
                        <>
                            <Link
                                to={`/routes/${route.id}/edit`}
                                className="px-3 py-1.5 text-sm bg-amber-500 hover:bg-amber-600 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg"
                            >
                                {t('routes.detail.editBtn')}
                            </Link>
                            <button
                                onClick={handleArchive}
                                disabled={actionLoading}
                                className="px-3 py-1.5 text-sm bg-red-500 hover:bg-red-600 text-white rounded-lg cursor-pointer disabled:opacity-50"
                            >
                                {t('routes.detail.archiveBtn')}
                            </button>
                        </>
                    )}
                    <a
                        href={routesService.exportUrl(route.id, 'gpx')}
                        className="px-3 py-1.5 text-sm bg-gray-50 dark:bg-stone-800 text-gray-700 dark:text-stone-200 border border-gray-300 dark:border-stone-600 rounded-lg hover:bg-gray-100 dark:hover:bg-stone-700"
                        title={t('routes.detail.gpxTitle')}
                    >
                        {t('routes.detail.gpxBtn')}
                    </a>
                    <a
                        href={routesService.exportUrl(route.id, 'kml')}
                        className="px-3 py-1.5 text-sm bg-gray-50 dark:bg-stone-800 text-gray-700 dark:text-stone-200 border border-gray-300 dark:border-stone-600 rounded-lg hover:bg-gray-100 dark:hover:bg-stone-700"
                        title={t('routes.detail.kmlTitle')}
                    >
                        {t('routes.detail.kmlBtn')}
                    </a>
                </div>

                {/* Map */}
                {coords.length > 0 && (
                    <div className="h-80 rounded-lg overflow-hidden border border-gray-200 dark:border-stone-700 mb-4">
                        <MapContainer center={coords[0]} zoom={10} scrollWheelZoom className="h-full w-full">
                            <ThemedTileLayer/>
                            <FitToStops coords={coords}/>
                            {coords.length >= 2 && (
                                <Polyline positions={coords} pathOptions={{color: '#d97706', weight: 4, opacity: 0.7}}/>
                            )}
                            {route.stops.map(s => (
                                <Marker
                                    key={s.id}
                                    position={[parseFloat(s.latitude), parseFloat(s.longitude)]}
                                    icon={numberedIcon(s.order, s.is_unavailable ? '#6b7280' : '#d97706')}
                                >
                                    <Popup>
                                        <strong>{s.order}. {s.object_title}</strong>
                                        {s.is_unavailable && (
                                            <p style={{color: '#dc2626', fontSize: '12px', margin: '4px 0 0'}}>
                                                {t('routes.detail.stopUnavailable')}
                                            </p>
                                        )}
                                        <p style={{margin: '4px 0 0'}}>
                                            <Link to={`/objects/${s.object_id}`}>{t('routes.detail.stopDetails')}</Link>
                                        </p>
                                    </Popup>
                                </Marker>
                            ))}
                        </MapContainer>
                    </div>
                )}

                {/* Description */}
                <div className="mb-6">
                    <p className="text-gray-700 dark:text-stone-200 whitespace-pre-line leading-relaxed">
                        {route.description}
                    </p>
                </div>

                {/* Stops list */}
                <h2 className="text-lg font-semibold text-gray-900 dark:text-stone-100 mb-3">
                    {t('routes.detail.stopsHeader')} ({route.stops.length})
                </h2>

                {isAuthenticated && totalCount > 0 && (
                    <div className="mb-4">
                        <div className="flex justify-between items-baseline mb-1">
                            <span className="text-sm font-medium text-gray-700 dark:text-stone-200">
                                {allVisited
                                    ? `🏆 ${t('routes.detail.routeCompleted')}`
                                    : t('routes.detail.progress', {visited: visitedCount, total: totalCount})}
                            </span>
                            <span className="text-sm text-gray-500 dark:text-stone-400">{progressPct}%</span>
                        </div>
                        <div className="w-full h-2 bg-gray-200 dark:bg-stone-700 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-green-500 dark:bg-green-400 transition-all"
                                style={{width: `${progressPct}%`}}
                            />
                        </div>
                        {!allVisited && (
                            <button
                                type="button"
                                onClick={handleMarkRouteCompleted}
                                disabled={actionLoading}
                                className="mt-2 px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50"
                            >
                                🏆 {t('routes.detail.markRouteCompleted')}
                            </button>
                        )}
                    </div>
                )}
                <div className="space-y-2">
                    {route.stops.map(s => (
                        <div
                            key={s.id}
                            className={`flex items-start gap-3 border rounded-lg px-3 py-2 ${
                                s.is_unavailable
                                    ? 'border-gray-300 dark:border-stone-600 bg-gray-50 dark:bg-stone-800/50 opacity-70'
                                    : s.is_visited
                                        ? 'border-green-300 dark:border-green-700 bg-green-50/30 dark:bg-green-900/10'
                                        : 'border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900'
                            }`}
                        >
                            <div className={`shrink-0 w-8 h-8 rounded-full text-white dark:text-stone-900 flex items-center justify-center font-bold ${
                                s.is_visited
                                    ? 'bg-green-600 dark:bg-green-500'
                                    : 'bg-amber-600 dark:bg-amber-500'
                            }`}>
                                {s.is_visited ? '✓' : s.order}
                            </div>
                            <div className="flex-1 min-w-0">
                                <Link
                                    to={`/objects/${s.object_id}`}
                                    className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300"
                                >
                                    {s.object_title}
                                </Link>
                                {s.is_unavailable && (
                                    <p className="text-xs text-red-600 dark:text-red-400">
                                        {t('routes.detail.stopUnavailable')}
                                    </p>
                                )}
                                {s.note && (
                                    <p className="text-sm text-gray-600 dark:text-stone-300 mt-1 italic">
                                        {s.note}
                                    </p>
                                )}
                            </div>
                            {isAuthenticated && !s.is_unavailable && (
                                <button
                                    type="button"
                                    onClick={() => handleToggleVisit(s.id, s.object_id)}
                                    disabled={togglingStopId === s.id}
                                    className={`shrink-0 px-2.5 py-1 text-xs rounded-lg cursor-pointer disabled:opacity-50 ${
                                        s.is_visited
                                            ? 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-300 border border-green-300 dark:border-green-700 hover:bg-green-200 dark:hover:bg-green-900/60'
                                            : 'bg-amber-500 hover:bg-amber-600 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900'
                                    }`}
                                    title={s.is_visited ? t('routes.detail.unvisit') : t('routes.detail.markVisited')}
                                >
                                    {s.is_visited ? `✓ ${t('routes.detail.visited')}` : t('routes.detail.iWasHere')}
                                </button>
                            )}
                        </div>
                    ))}
                </div>

                {route.copied_from && (
                    <p className="text-xs text-gray-500 dark:text-stone-400 mt-4">
                        {t('routes.detail.copiedFrom')}{' '}
                        <Link to={`/routes/${route.copied_from}`} className="text-amber-700 dark:text-amber-400 hover:underline">
                            #{route.copied_from}
                        </Link>
                    </p>
                )}
            </div>
        </div>
    );
}
