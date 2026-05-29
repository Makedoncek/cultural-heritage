import L from 'leaflet';
import {Marker, Popup} from 'react-leaflet';
import {useNavigate} from 'react-router';
import {useTranslation} from 'react-i18next';
import CoverImage from '../Objects/CoverImage';
import type {CulturalObject} from '../../types';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIconGrey from '../../assets/marker-icon-grey.png';
import markerIconGrey2x from '../../assets/marker-icon-2x-grey.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

const iconOptions = {
    iconSize: [25, 41] as [number, number],
    iconAnchor: [12, 41] as [number, number],
    popupAnchor: [1, -34] as [number, number],
    shadowSize: [41, 41] as [number, number],
    shadowUrl: markerShadow,
};

const defaultIcon = new L.Icon({
    ...iconOptions,
    iconUrl: markerIcon,
    iconRetinaUrl: markerIcon2x,
});

const pendingIcon = new L.Icon({
    ...iconOptions,
    iconUrl: markerIconGrey,
    iconRetinaUrl: markerIconGrey2x,
});

// Purple marker for events via inline SVG
const eventMarkerSvg = encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41">
  <path d="M12.5 0C5.6 0 0 5.6 0 12.5C0 21.9 12.5 41 12.5 41S25 21.9 25 12.5C25 5.6 19.4 0 12.5 0Z" fill="#9333ea"/>
  <circle cx="12.5" cy="12.5" r="6" fill="#fff"/>
</svg>`);

const eventIcon = new L.Icon({
    ...iconOptions,
    iconUrl: `data:image/svg+xml,${eventMarkerSvg}`,
    iconRetinaUrl: `data:image/svg+xml,${eventMarkerSvg}`,
});

// Green marker for objects the current user has already visited.
const visitedMarkerSvg = (color: string) => encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41">
  <path d="M12.5 0C5.6 0 0 5.6 0 12.5C0 21.9 12.5 41 12.5 41S25 21.9 25 12.5C25 5.6 19.4 0 12.5 0Z" fill="${color}"/>
  <path d="M8 13 L11.5 16 L17 9" stroke="#fff" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`);

const visitedEventIcon = new L.Icon({
    ...iconOptions,
    iconUrl: `data:image/svg+xml,${visitedMarkerSvg('#16a34a')}`,
    iconRetinaUrl: `data:image/svg+xml,${visitedMarkerSvg('#16a34a')}`,
});

const visitedPermanentIcon = new L.Icon({
    ...iconOptions,
    iconUrl: `data:image/svg+xml,${visitedMarkerSvg('#15803d')}`,
    iconRetinaUrl: `data:image/svg+xml,${visitedMarkerSvg('#15803d')}`,
});

function formatDateRange(start: string | null, end: string | null, locale: string): string | null {
    if (!start || !end) return null;
    const fmt = (d: string) => new Date(d).toLocaleString(locale, {day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'});
    return `${fmt(start)} — ${fmt(end)}`;
}

interface ObjectMarkerProps {
    object: CulturalObject;
}

export default function ObjectMarker({object}: Readonly<ObjectMarkerProps>) {
    const navigate = useNavigate();
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const isPending = object.status === 'pending';
    const isEvent = object.object_type === 'event';
    const isVisited = object.is_visited === true;
    const icon = isPending
        ? pendingIcon
        : isVisited
            ? (isEvent ? visitedEventIcon : visitedPermanentIcon)
            : isEvent
                ? eventIcon
                : defaultIcon;
    const dateRange = isEvent ? formatDateRange(object.event_start_date, object.event_end_date, dateLocale) : null;

    return (
        <Marker
            position={[Number.parseFloat(object.latitude), Number.parseFloat(object.longitude)]}
            icon={icon}
        >
            <Popup>
                <div className="w-48">
                    <CoverImage
                        coverUrl={object.cover_url}
                        tags={object.tags}
                        alt={object.title}
                        className="w-full h-24 rounded mb-2"
                    />
                </div>
                <h3 className="font-bold text-sm mb-1">{object.title}</h3>
                {isPending && (
                    <span className="inline-block px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs mb-2">
                        {t('object.moderationStatus.pending')}
                    </span>
                )}
                {isEvent && (
                    <span className="inline-block px-1.5 py-0.5 bg-purple-100 text-purple-800 rounded text-xs mb-2">
                        {t('object.objectType.event')}
                    </span>
                )}
                {dateRange && (
                    <p className="text-xs text-gray-600 mb-2">📅 {dateRange}</p>
                )}
                {object.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                        {object.tags.map(tag => (
                            <span
                                key={tag.id}
                                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded text-xs"
                            >
                                {tag.icon} {tag.name}
                            </span>
                        ))}
                    </div>
                )}
                <button
                    onClick={() => navigate(`/objects/${object.id}`)}
                    className="text-xs text-blue-600 hover:text-blue-800 underline cursor-pointer"
                >
                    {t('home.details')}
                </button>
            </Popup>
        </Marker>
    );
}
