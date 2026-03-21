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

interface ObjectMarkerProps {
    object: CulturalObject;
}

export default function ObjectMarker({object}: ObjectMarkerProps) {
    const navigate = useNavigate();
    const isPending = object.status === 'pending';

    return (
        <Marker
            position={[parseFloat(object.latitude), parseFloat(object.longitude)]}
            icon={isPending ? pendingIcon : defaultIcon}
        >
            <Popup>
                <h3 className="font-bold text-sm mb-1">{object.title}</h3>
                {isPending && (
                    <span className="inline-block px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs mb-2">
                        На модерації
                    </span>
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