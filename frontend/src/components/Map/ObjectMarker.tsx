import L from 'leaflet';
import {Marker, Popup} from 'react-leaflet';
import {useNavigate} from 'react-router';
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

function formatDateRange(start: string | null, end: string | null): string | null {
    if (!start || !end) return null;
    const fmt = (d: string) => new Date(d).toLocaleDateString('uk-UA', {day: '2-digit', month: '2-digit', year: 'numeric'});
    return `${fmt(start)} — ${fmt(end)}`;
}

interface ObjectMarkerProps {
    object: CulturalObject;
}

export default function ObjectMarker({object}: ObjectMarkerProps) {
    const navigate = useNavigate();
    const isPending = object.status === 'pending';
    const isEvent = object.object_type === 'event';
    const icon = isPending ? pendingIcon : isEvent ? eventIcon : defaultIcon;
    const dateRange = isEvent ? formatDateRange(object.event_start_date, object.event_end_date) : null;

    return (
        <Marker
            position={[parseFloat(object.latitude), parseFloat(object.longitude)]}
            icon={icon}
        >
            <Popup>
                <h3 className="font-bold text-sm mb-1">{object.title}</h3>
                {isPending && (
                    <span className="inline-block px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs mb-2">
                        На модерації
                    </span>
                )}
                {isEvent && (
                    <span className="inline-block px-1.5 py-0.5 bg-purple-100 text-purple-800 rounded text-xs mb-2">
                        Подія
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
                    Детальніше
                </button>
            </Popup>
        </Marker>
    );
}
