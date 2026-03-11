import '../../utils/leaflet-fix';
import {MapContainer, TileLayer} from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import ObjectMarker from './ObjectMarker';
import type {CulturalObject} from '../../types';
import type {LatLngBoundsExpression} from 'leaflet';

const UKRAINE_BOUNDS: LatLngBoundsExpression = [
    [44.2, 22.0],  // southwest
    [52.4, 40.3],  // northeast
];

interface MapViewProps {
    objects: CulturalObject[];
}

export default function MapView({objects}: MapViewProps) {
    return (
        <MapContainer
            center={[49.0, 32.0]}
            zoom={7}
            minZoom={6}
            maxBounds={UKRAINE_BOUNDS}
            maxBoundsViscosity={1.0}
            scrollWheelZoom={true}
            className="absolute inset-0"
        >
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <MarkerClusterGroup chunkedLoading key={objects.map(o => o.id).join(',')}>
                {objects.map(obj => (
                    <ObjectMarker key={obj.id} object={obj}/>
                ))}
            </MarkerClusterGroup>
        </MapContainer>
    );
}