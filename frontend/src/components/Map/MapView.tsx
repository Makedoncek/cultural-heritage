import '../../utils/leaflet-fix';
import {useEffect} from 'react';
import {MapContainer, useMap} from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import ObjectMarker from './ObjectMarker';
import ThemedTileLayer from './ThemedTileLayer';
import type {MapCulturalObject} from '../../types';
import type {LatLngBoundsExpression} from 'leaflet';

const UKRAINE_BOUNDS: LatLngBoundsExpression = [
    [44.2, 22],
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
    objects: MapCulturalObject[];
    flyTo?: FlyToTarget | null;
}

export default function MapView({objects, flyTo = null}: Readonly<MapViewProps>) {
    return (
        <MapContainer
            center={[49, 32]}
            zoom={7}
            minZoom={6}
            maxBounds={UKRAINE_BOUNDS}
            maxBoundsViscosity={1}
            scrollWheelZoom={true}
            className="absolute inset-0"
        >
            <FlyToHandler target={flyTo} />
            <ThemedTileLayer/>
            <MarkerClusterGroup chunkedLoading key={objects.map(o => o.id).join(',')}>
                {objects.map(obj => (
                    <ObjectMarker key={obj.id} object={obj}/>
                ))}
            </MarkerClusterGroup>
        </MapContainer>
    );
}