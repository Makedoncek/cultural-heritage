import '../../utils/leaflet-fix';
import {useEffect} from 'react';
import {MapContainer, TileLayer, useMap} from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import ObjectMarker from './ObjectMarker';
import type {CulturalObject} from '../../types';
import type {LatLngBoundsExpression} from 'leaflet';

const UKRAINE_BOUNDS: LatLngBoundsExpression = [
    [44.2, 22.0],
    [52.4, 40.3],
];

export interface FlyToTarget {
    latitude: number;
    longitude: number;
}

function FlyToHandler({target}: {target: FlyToTarget | null}) {
    const map = useMap();
    useEffect(() => {
        if (target) map.flyTo([target.latitude, target.longitude], 14, {duration: 1});
    }, [target, map]);
    return null;
}

interface MapViewProps {
    objects: CulturalObject[];
    flyTo?: FlyToTarget | null;
}

export default function MapView({objects, flyTo = null}: MapViewProps) {
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
            <FlyToHandler target={flyTo} />
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