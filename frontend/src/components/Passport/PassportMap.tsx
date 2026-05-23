import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {MapContainer, Marker, Popup, useMap} from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import L from 'leaflet';
import {useTranslation} from 'react-i18next';
import ThemedTileLayer from '../Map/ThemedTileLayer';
import type {Visit, PlannedVisit} from '../../types/visits';
import '../../utils/leaflet-fix';

type Kind = 'visited' | 'planned';

interface Point {
    kind: Kind;
    id: number;
    objectId: number;
    title: string;
    lat: number;
    lng: number;
    visitedAt?: string;
    plannedDate?: string | null;
}

function pinIcon(kind: Kind): L.DivIcon {
    const isVisited = kind === 'visited';
    const bg = isVisited ? '#16a34a' : '#2563eb';
    const symbol = isVisited ? '✓' : '📌';
    const fontSize = isVisited ? '16px' : '13px';
    return L.divIcon({
        html: `<div style="background:${bg};color:#fff;border:2px solid #fff;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:${fontSize};box-shadow:0 2px 4px rgba(0,0,0,0.4);">${symbol}</div>`,
        className: 'passport-marker',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
}

function FitToPoints({points}: {points: Point[]}) {
    const map = useMap();
    useEffect(() => {
        if (points.length === 0) return;
        if (points.length === 1) {
            map.setView([points[0].lat, points[0].lng], 12);
        } else {
            map.fitBounds(points.map(p => [p.lat, p.lng] as [number, number]), {padding: [40, 40]});
        }
    }, [points, map]);
    return null;
}

interface Props {
    visits: Visit[];
    planned: PlannedVisit[];
}

export default function PassportMap({visits, planned}: Props) {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const [fullscreen, setFullscreen] = useState(false);

    useEffect(() => {
        if (!fullscreen) return;
        const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setFullscreen(false); };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [fullscreen]);

    const points: Point[] = [
        ...visits
            .filter(v => v.object_latitude && v.object_longitude)
            .map(v => ({
                kind: 'visited' as const,
                id: v.id,
                objectId: v.object_id,
                title: v.object_title,
                lat: parseFloat(v.object_latitude),
                lng: parseFloat(v.object_longitude),
                visitedAt: v.visited_at,
            })),
        ...planned
            .filter(p => p.object_latitude && p.object_longitude)
            .map(p => ({
                kind: 'planned' as const,
                id: p.id,
                objectId: p.object_id,
                title: p.object_title,
                lat: parseFloat(p.object_latitude),
                lng: parseFloat(p.object_longitude),
                plannedDate: p.planned_date,
            })),
    ];

    const renderMarkers = (onPopupLinkClick?: () => void) => (
        <MarkerClusterGroup chunkedLoading>
            {points.map(p => (
                <Marker key={`${p.kind}-${p.id}`} position={[p.lat, p.lng]} icon={pinIcon(p.kind)}>
                    <Popup>
                        <strong>{p.title}</strong>
                        <p style={{margin: '4px 0 0', fontSize: '12px', color: '#6b7280'}}>
                            {p.kind === 'visited' && p.visitedAt
                                ? t('passport.popupVisited', {date: new Date(p.visitedAt).toLocaleString(dateLocale, {dateStyle: 'short', timeStyle: 'short'})})
                                : p.kind === 'planned' && p.plannedDate
                                    ? t('passport.popupPlanned', {date: new Date(p.plannedDate).toLocaleDateString(dateLocale)})
                                    : t('passport.popupPlannedNoDate')}
                        </p>
                        <p style={{margin: '6px 0 0'}}>
                            <Link to={`/objects/${p.objectId}`} onClick={onPopupLinkClick}>
                                {t('passport.objectDetails')}
                            </Link>
                        </p>
                    </Popup>
                </Marker>
            ))}
        </MarkerClusterGroup>
    );

    const center: [number, number] = points.length > 0 ? [points[0].lat, points[0].lng] : [49.0, 32.0];
    const zoom = points.length > 0 ? 7 : 6;

    return (
        <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-stone-100 mb-1">
                🗺 {t('passport.mapTitle')}
            </h2>
            <p className="text-xs text-gray-500 dark:text-stone-400 mb-3">
                {t('passport.mapSubtitle')}
            </p>

            {points.length === 0 ? (
                <div className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-6 text-center text-sm text-gray-500 dark:text-stone-400">
                    {t('passport.mapEmpty')}
                </div>
            ) : (
                <>
                    <div className="relative h-80 rounded-lg overflow-hidden border border-gray-200 dark:border-stone-700">
                        <MapContainer center={center} zoom={zoom} scrollWheelZoom className="h-full w-full">
                            <ThemedTileLayer/>
                            <FitToPoints points={points}/>
                            {renderMarkers()}
                        </MapContainer>
                        <button
                            type="button"
                            onClick={() => setFullscreen(true)}
                            className="absolute top-2 right-2 z-[1000] bg-white dark:bg-stone-800 border border-gray-300 dark:border-stone-600 rounded-lg px-2.5 py-1.5 text-sm text-gray-700 dark:text-stone-200 hover:bg-gray-50 dark:hover:bg-stone-700 shadow-sm cursor-pointer"
                            title={t('passport.fullscreen')}
                        >
                            ⛶
                        </button>
                        <div className="absolute bottom-2 left-2 z-[1000] bg-white/95 dark:bg-stone-800/95 border border-gray-300 dark:border-stone-600 rounded-lg px-2.5 py-1.5 text-xs text-gray-700 dark:text-stone-200 shadow-sm flex flex-col gap-1">
                            <span className="inline-flex items-center gap-1.5">
                                <span className="inline-block w-3 h-3 rounded-full bg-green-600 dark:bg-green-500"/>
                                {t('passport.legendVisited')} ({visits.length})
                            </span>
                            <span className="inline-flex items-center gap-1.5">
                                <span className="inline-block w-3 h-3 rounded-full bg-blue-600 dark:bg-blue-500"/>
                                {t('passport.legendPlanned')} ({planned.length})
                            </span>
                        </div>
                    </div>

                    {fullscreen && (
                        <div className="fixed inset-0 z-[9999] bg-white dark:bg-stone-950 flex flex-col">
                            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-stone-700">
                                <span className="text-sm text-gray-700 dark:text-stone-200 font-medium truncate">
                                    🗺 {t('passport.mapTitle')}
                                </span>
                                <button
                                    type="button"
                                    onClick={() => setFullscreen(false)}
                                    className="px-3 py-1.5 text-sm bg-gray-200 dark:bg-stone-700 text-gray-700 dark:text-stone-200 rounded-lg hover:bg-gray-300 dark:hover:bg-stone-600 cursor-pointer"
                                >
                                    ✕ {t('passport.exitFullscreen')}
                                </button>
                            </div>
                            <div className="flex-1 relative">
                                <MapContainer center={center} zoom={zoom} scrollWheelZoom className="h-full w-full">
                                    <ThemedTileLayer/>
                                    <FitToPoints points={points}/>
                                    {renderMarkers(() => setFullscreen(false))}
                                </MapContainer>
                                <div className="absolute bottom-3 left-3 z-[1000] bg-white/95 dark:bg-stone-800/95 border border-gray-300 dark:border-stone-600 rounded-lg px-3 py-2 text-sm text-gray-700 dark:text-stone-200 shadow flex flex-col gap-1">
                                    <span className="inline-flex items-center gap-2">
                                        <span className="inline-block w-3 h-3 rounded-full bg-green-600 dark:bg-green-500"/>
                                        {t('passport.legendVisited')} ({visits.length})
                                    </span>
                                    <span className="inline-flex items-center gap-2">
                                        <span className="inline-block w-3 h-3 rounded-full bg-blue-600 dark:bg-blue-500"/>
                                        {t('passport.legendPlanned')} ({planned.length})
                                    </span>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
