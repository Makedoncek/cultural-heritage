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
import ContentLanguageSelector, {type ContentLanguage} from '../components/Translation/ContentLanguageSelector';
import TranslationSubmitModal from '../components/Translation/TranslationSubmitModal';
import ReportInaccuracyButton from '../components/Objects/ReportInaccuracyButton';
import type {RouteDetail} from '../types/routes';
import '../utils/leaflet-fix';

const ALL_CONTENT_LANGUAGES: ContentLanguage[] = ['uk', 'en', 'pl', 'de'];

function numberedIcon(n: number, color = '#d97706', visited = false): L.DivIcon {
    const bg = visited ? '#16a34a' : color;
    const badge = visited
        ? `<div style="position:absolute;top:-4px;right:-4px;background:#fff;color:#16a34a;border:2px solid #16a34a;border-radius:50%;width:14px;height:14px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:10px;line-height:1;">✓</div>`
        : '';
    return L.divIcon({
        html: `<div style="position:relative;width:28px;height:28px;"><div style="background:${bg};color:#fff;border:2px solid #fff;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;box-shadow:0 2px 4px rgba(0,0,0,0.4);">${n}</div>${badge}</div>`,
        className: 'route-stop-marker',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
}

function formatDuration(seconds: number, t: (key: string) => string): string {
    const totalMin = Math.round(seconds / 60);
    if (totalMin < 60) return `${totalMin} ${t('routes.minutes')}`;
    const hours = Math.floor(totalMin / 60);
    const min = totalMin % 60;
    return min === 0 ? `${hours} ${t('routes.hours')}` : `${hours} ${t('routes.hours')} ${min} ${t('routes.minutes')}`;
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
    const [mapFullscreen, setMapFullscreen] = useState(false);
    const [profile, setProfile] = useState<'foot-walking' | 'cycling-regular' | 'driving-car'>('foot-walking');
    const [showTranslationModal, setShowTranslationModal] = useState(false);
    const [contentLang, setContentLang] = useState<ContentLanguage | null>(null);

    useEffect(() => {
        if (!mapFullscreen) return;
        const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setMapFullscreen(false); };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [mapFullscreen]);

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

    const translateOrsMessage = (raw: string): string => {
        // Backend injects «Object title» between coordinate index and the (lng,lat) tuple.
        const titleRe = '«([^»]+)»\\s*';
        const fmtTitle = (s?: string) => s ? `«${s}» ` : '';

        // Directions 2010 — point outside any road network.
        const m1 = raw.match(new RegExp(`Could not find routable point within a radius of ([\\d.]+) meters of specified coordinate (\\d+)(?:\\s+${titleRe})?\\s*[(:]?\\s*([\\d.\\-]+)[, ]\\s*([\\d.\\-]+)`, 'i'));
        if (m1) {
            return t('routes.toast.orsErr.unroutablePoint', {
                radius: m1[1], index: m1[2], title: fmtTitle(m1[3]), lng: m1[4], lat: m1[5],
            });
        }
        // Directions 2009 — pair unreachable in current profile.
        const m2 = raw.match(new RegExp(`points (\\d+)(?:\\s+${titleRe})?\\s*\\(?([\\d.\\-]+)[, ]\\s*([\\d.\\-]+)\\)? and (\\d+)(?:\\s+${titleRe})?\\s*\\(?([\\d.\\-]+)[, ]\\s*([\\d.\\-]+)`, 'i'));
        if (m2) {
            return t('routes.toast.orsErr.unreachablePair', {
                a: m2[1], titleA: fmtTitle(m2[2]), aLng: m2[3], aLat: m2[4],
                b: m2[5], titleB: fmtTitle(m2[6]), bLng: m2[7], bLat: m2[8],
            });
        }
        // Optimization (vroom) — unfound location.
        const m3 = raw.match(new RegExp(`Unfound route\\(s\\) from location (?:${titleRe})?\\[([\\d.\\-]+)[, ]\\s*([\\d.\\-]+)\\]`, 'i'));
        if (m3) {
            return t('routes.toast.orsErr.unfoundLocation', {
                title: fmtTitle(m3[1]), lng: m3[2], lat: m3[3],
            });
        }
        return raw;  // unknown English message — show as-is
    };

    const showOrsErrorToast = (rawDetail: string | undefined, fallback: string) => {
        const message = rawDetail ? translateOrsMessage(rawDetail) : fallback;
        const isPointIssue = rawDetail && /Could not find routable point|coordinate \d+:/i.test(rawDetail);
        const isPairIssue = rawDetail && (/Unable to find a route|between points/i.test(rawDetail) || /Unfound route/i.test(rawDetail));
        const hint = isPointIssue
            ? t('routes.toast.hintPointOffRoad')
            : isPairIssue
                ? t('routes.toast.hintTryAnotherProfile')
                : null;
        toast.error(
            (tInst) => (
                <div className="flex flex-col gap-2 max-w-md">
                    <p className="text-sm font-medium leading-snug">{message}</p>
                    {hint && (
                        <p className="text-xs leading-snug opacity-80 border-t border-current/20 pt-2">
                            {hint}
                        </p>
                    )}
                    <button
                        type="button"
                        onClick={() => toast.dismiss(tInst.id)}
                        className="self-end text-xs underline opacity-70 hover:opacity-100 cursor-pointer"
                    >
                        {t('routes.toast.dismiss')}
                    </button>
                </div>
            ),
            {duration: 10000},
        );
    };

    const handleComputeGeometry = async () => {
        if (!route) return;
        setActionLoading(true);
        try {
            const result = await routesService.computeGeometry(route.id, profile);
            setRoute(prev => prev ? {
                ...prev,
                route_geometry: result.geometry,
                route_distance_m: result.distance_m,
                route_duration_s: result.duration_s,
            } : prev);
            toast.success(t('routes.toast.geometryComputed'));
        } catch (e) {
            const detail = (e as {response?: {data?: {detail?: string}}}).response?.data?.detail;
            showOrsErrorToast(detail, t('routes.toast.geometryFailed'));
        } finally {
            setActionLoading(false);
        }
    };

    const handleOptimizeOrder = async () => {
        if (!route) return;
        if (!confirm(t('routes.detail.optimizeConfirm'))) return;
        setActionLoading(true);
        try {
            await routesService.optimizeOrder(route.id, profile);
            const fresh = await routesService.detail(route.id);
            setRoute(fresh);
            toast.success(t('routes.toast.orderOptimized'));
        } catch (e) {
            const detail = (e as {response?: {data?: {detail?: string}}}).response?.data?.detail;
            showOrsErrorToast(detail, t('routes.toast.optimizeFailed'));
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
            .then(data => {
                setRoute(data);
                const uiLang = (i18n.resolvedLanguage || 'uk') as ContentLanguage;
                setContentLang(data.available_languages.includes(uiLang) ? uiLang : data.original_language);
            })
            .catch(() => setError(t('routes.toast.loadFailed')))
            .finally(() => setLoading(false));
    }, [routeId, t, i18n]);

    const handleSelectContentLang = (lang: ContentLanguage) => {
        if (routeId == null || lang === contentLang) return;
        setContentLang(lang);
        routesService.detail(routeId, lang)
            .then(setRoute)
            .catch(() => toast.error(t('routes.toast.loadFailed')));
    };

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
    // ORS returns [lng, lat]; Leaflet expects [lat, lng] — swap.
    const realRoadCoords: [number, number][] | null = route.route_geometry
        ? route.route_geometry.map(([lng, lat]) => [lat, lng])
        : null;

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto px-4 py-6">
                <Link to="/routes" className="text-sm text-amber-700 dark:text-amber-400 hover:underline mb-2 inline-block">
                    {t('routes.detail.back')}
                </Link>

                <ContentLanguageSelector
                    available={route.available_languages}
                    selected={contentLang ?? route.original_language}
                    onSelect={handleSelectContentLang}
                    onSuggest={isAuthenticated ? () => setShowTranslationModal(true) : undefined}
                />
                {isAuthenticated && route.current_translation_id && (
                    <div className="-mt-1 mb-3">
                        <ReportInaccuracyButton
                            targetType="route_translation"
                            targetId={route.current_translation_id}
                            targetTitle={route.title}
                            compact
                        />
                    </div>
                )}

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
                                className="px-3 py-1.5 text-sm bg-stone-200 hover:bg-stone-300 dark:bg-stone-700 dark:hover:bg-stone-600 text-stone-700 dark:text-stone-200 rounded-lg cursor-pointer disabled:opacity-50"
                            >
                                📦 {t('routes.detail.archiveBtn')}
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
                    <a
                        href={routesService.exportUrl(route.id, 'kmz')}
                        className="px-3 py-1.5 text-sm bg-gray-50 dark:bg-stone-800 text-gray-700 dark:text-stone-200 border border-gray-300 dark:border-stone-600 rounded-lg hover:bg-gray-100 dark:hover:bg-stone-700"
                        title={t('routes.detail.kmzTitle')}
                    >
                        {t('routes.detail.kmzBtn')}
                    </a>
                    {isAuthenticated && !isOwner && (
                        <ReportInaccuracyButton targetType="route" targetId={route.id} targetTitle={route.title}/>
                    )}
                    {route.visibility === 'public' && route.status === 'approved' && (
                        <button
                            type="button"
                            onClick={async () => {
                                const url = `${window.location.origin}/routes/${route.id}`;
                                // Use native share only on touch-primary devices (phones/tablets) —
                                // on desktop the OS share dialog feels foreign for a web app.
                                const isTouchPrimary = window.matchMedia('(pointer: coarse)').matches;
                                try {
                                    if (isTouchPrimary && navigator.share) {
                                        await navigator.share({title: route.title, url});
                                    } else {
                                        await navigator.clipboard.writeText(url);
                                        toast.success(t('routes.toast.linkCopied'));
                                    }
                                } catch {
                                    // user cancelled share dialog — silent
                                }
                            }}
                            className="px-3 py-1.5 text-sm bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 rounded-lg hover:bg-amber-200 dark:hover:bg-amber-900/60 cursor-pointer"
                            title={t('routes.detail.shareTitle')}
                        >
                            🔗 {t('routes.detail.shareBtn')}
                        </button>
                    )}
                </div>

                {/* Route stats */}
                {coords.length > 0 && (
                    <div className="mb-3 text-sm">
                        {route.route_distance_m != null && route.route_duration_s != null ? (
                            <span className="inline-flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-stone-800 border border-amber-200 dark:border-stone-700 rounded-lg text-gray-800 dark:text-stone-100">
                                <strong>🛣 {(route.route_distance_m / 1000).toFixed(1)} км</strong>
                                <span className="text-gray-500 dark:text-stone-400">·</span>
                                <strong>⏱ {formatDuration(route.route_duration_s, t)}</strong>
                                <span className="text-xs text-gray-500 dark:text-stone-400">({t('routes.detail.realRoads')})</span>
                            </span>
                        ) : coords.length >= 2 && (
                            <span className="text-xs text-gray-500 dark:text-stone-400 italic">
                                {t('routes.detail.straightLineHint')}
                            </span>
                        )}
                    </div>
                )}

                {/* ORS controls — own row so the buttons stay together */}
                {canEdit && coords.length >= 2 && (
                    <div className="flex flex-wrap items-center gap-2 mb-3 text-sm">
                        <div className="inline-flex rounded-lg border border-gray-300 dark:border-stone-600 overflow-hidden" role="group">
                            {(['foot-walking', 'cycling-regular', 'driving-car'] as const).map(p => {
                                const icon = p === 'foot-walking' ? '🚶' : p === 'cycling-regular' ? '🚲' : '🚗';
                                const isActive = profile === p;
                                return (
                                    <button
                                        key={p}
                                        type="button"
                                        onClick={() => setProfile(p)}
                                        disabled={actionLoading}
                                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors cursor-pointer disabled:opacity-50 ${
                                            isActive
                                                ? 'bg-amber-500 text-white dark:bg-amber-400 dark:text-stone-900'
                                                : 'bg-white dark:bg-stone-800 text-gray-700 dark:text-stone-200 hover:bg-gray-100 dark:hover:bg-stone-700'
                                        }`}
                                    >
                                        <span>{icon}</span>
                                        <span className="hidden sm:inline">{t(`routes.detail.profile.${p}`)}</span>
                                    </button>
                                );
                            })}
                        </div>
                        <button
                            type="button"
                            onClick={handleComputeGeometry}
                            disabled={actionLoading}
                            className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400 text-white rounded-lg cursor-pointer disabled:opacity-50"
                            title={t('routes.detail.computeGeometryHint')}
                        >
                            🛣 {t('routes.detail.computeGeometry')}
                        </button>
                        {coords.length >= 3 && (
                            <button
                                type="button"
                                onClick={handleOptimizeOrder}
                                disabled={actionLoading}
                                className="px-3 py-1.5 text-sm bg-purple-600 hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-400 text-white rounded-lg cursor-pointer disabled:opacity-50"
                                title={t('routes.detail.optimizeHint')}
                            >
                                ⚡ {t('routes.detail.optimize')}
                            </button>
                        )}
                    </div>
                )}

                {/* Map */}
                {coords.length > 0 && (
                    <div className="relative h-80 rounded-lg overflow-hidden border border-gray-200 dark:border-stone-700 mb-4">
                        <MapContainer center={coords[0]} zoom={10} scrollWheelZoom className="h-full w-full">
                            <ThemedTileLayer/>
                            <FitToStops coords={coords}/>
                            {realRoadCoords ? (
                                <Polyline positions={realRoadCoords} pathOptions={{color: '#d97706', weight: 4, opacity: 0.85}}/>
                            ) : coords.length >= 2 ? (
                                <Polyline positions={coords} pathOptions={{color: '#d97706', weight: 4, opacity: 0.7, dashArray: '8 6'}}/>
                            ) : null}
                            {route.stops.map(s => (
                                <Marker
                                    key={s.id}
                                    position={[parseFloat(s.latitude), parseFloat(s.longitude)]}
                                    icon={numberedIcon(s.order, s.is_unavailable ? '#6b7280' : '#d97706', s.is_visited && !s.is_unavailable)}
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
                        <button
                            type="button"
                            onClick={() => setMapFullscreen(true)}
                            className="absolute top-2 right-2 z-[1000] bg-white dark:bg-stone-800 border border-gray-300 dark:border-stone-600 rounded-lg px-2.5 py-1.5 text-sm text-gray-700 dark:text-stone-200 hover:bg-gray-50 dark:hover:bg-stone-700 shadow-sm cursor-pointer"
                            title={t('routes.detail.fullscreen')}
                        >
                            ⛶
                        </button>
                    </div>
                )}

                {/* Fullscreen overlay */}
                {mapFullscreen && coords.length > 0 && (
                    <div className="fixed inset-0 z-[9999] bg-white dark:bg-stone-950 flex flex-col">
                        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-stone-700">
                            <span className="text-sm text-gray-700 dark:text-stone-200 font-medium truncate">
                                🗺 {route.title}
                            </span>
                            <button
                                type="button"
                                onClick={() => setMapFullscreen(false)}
                                className="px-3 py-1.5 text-sm bg-gray-200 dark:bg-stone-700 text-gray-700 dark:text-stone-200 rounded-lg hover:bg-gray-300 dark:hover:bg-stone-600 cursor-pointer"
                            >
                                ✕ {t('routes.detail.exitFullscreen')}
                            </button>
                        </div>
                        <div className="flex-1">
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
                                        icon={numberedIcon(s.order, s.is_unavailable ? '#6b7280' : '#d97706', s.is_visited && !s.is_unavailable)}
                                    >
                                        <Popup>
                                            <strong>{s.order}. {s.object_title}</strong>
                                            {s.is_unavailable && (
                                                <p style={{color: '#dc2626', fontSize: '12px', margin: '4px 0 0'}}>
                                                    {t('routes.detail.stopUnavailable')}
                                                </p>
                                            )}
                                            <p style={{margin: '4px 0 0'}}>
                                                <Link to={`/objects/${s.object_id}`} onClick={() => setMapFullscreen(false)}>
                                                    {t('routes.detail.stopDetails')}
                                                </Link>
                                            </p>
                                        </Popup>
                                    </Marker>
                                ))}
                            </MapContainer>
                        </div>
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

            <TranslationSubmitModal
                open={showTranslationModal}
                onClose={() => setShowTranslationModal(false)}
                targetOptions={ALL_CONTENT_LANGUAGES}
                originalLanguage={route.original_language}
                onSubmit={async payload => {
                    await routesService.submitTranslation(route.id, payload);
                }}
            />
        </div>
    );
}
