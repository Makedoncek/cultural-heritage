import {useEffect} from 'react';
import {MapContainer, TileLayer, Marker, useMap, useMapEvents} from 'react-leaflet';
import '../../utils/leaflet-fix';
import type {LatLngBoundsExpression} from 'leaflet';

const UKRAINE_BOUNDS: LatLngBoundsExpression = [
    [44.2, 22.0],
    [52.4, 40.3],
];

interface Coordinates {
    latitude: number;
    longitude: number;
}

interface LocationPickerProps {
    value: Coordinates | null;
    onChange: (coords: Coordinates) => void;
    error?: string;
}

function ClickHandler({onChange}: { onChange: (coords: Coordinates) => void }) {
    useMapEvents({
        click(e) {
            onChange({latitude: e.latlng.lat, longitude: e.latlng.lng});
        },
    });
    return null;
}

function CenterOnValue({value}: { value: Coordinates }) {
    const map = useMap();
    useEffect(() => {
        map.setView([value.latitude, value.longitude], 10);
    }, []);
    return null;
}

export default function LocationPicker({value, onChange, error}: LocationPickerProps) {
    return (
        <div>
            <div className="h-64 rounded-lg overflow-hidden border border-gray-200">
                <MapContainer
                    center={value ? [value.latitude, value.longitude] : [49.0, 32.0]}
                    zoom={value ? 10 : 6}
                    minZoom={6}
                    maxBounds={UKRAINE_BOUNDS}
                    maxBoundsViscosity={1.0}
                    scrollWheelZoom={true}
                    className="h-full w-full"
                >
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <ClickHandler onChange={onChange}/>
                    {value && <Marker position={[value.latitude, value.longitude]}/>}
                    {value && <CenterOnValue value={value}/>}
                </MapContainer>
            </div>
            <p className="text-sm mt-1.5 text-gray-500">
                {value
                    ? `${value.latitude.toFixed(6)}, ${value.longitude.toFixed(6)}`
                    : 'Натисніть на карту, щоб обрати місцезнаходження'
                }
            </p>
            {error && <p className="text-red-600 text-sm mt-1">{error}</p>}
        </div>
    );
}
