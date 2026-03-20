import {useState, useEffect, useRef} from 'react';
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

// Fly to value when flyKey changes (used to sync inline map after fullscreen close)
function FlyToValue({value, flyKey}: { value: Coordinates | null; flyKey: number }) {
    const map = useMap();
    const initialRef = useRef(true);
    useEffect(() => {
        if (initialRef.current) {
            // On mount: set view without animation if value exists (edit mode)
            if (value) map.setView([value.latitude, value.longitude], 10);
            initialRef.current = false;
            return;
        }
        if (value) map.flyTo([value.latitude, value.longitude], 12, {duration: 0.5});
    }, [flyKey]);
    return null;
}

function LocateMe({onLocate, large}: { onLocate: (coords: Coordinates) => void; large?: boolean }) {
    const map = useMap();
    const [locating, setLocating] = useState(false);

    const handleLocate = () => {
        if (!navigator.geolocation) return;
        setLocating(true);
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const coords = {latitude: pos.coords.latitude, longitude: pos.coords.longitude};
                onLocate(coords);
                map.flyTo([coords.latitude, coords.longitude], 14, {duration: 1});
                setLocating(false);
            },
            () => setLocating(false),
            {enableHighAccuracy: true, timeout: 10000},
        );
    };

    if (!navigator.geolocation) return null;

    return (
        <button
            type="button"
            onClick={handleLocate}
            disabled={locating}
            className={`absolute z-[1000] bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 shadow-sm cursor-pointer disabled:opacity-50 ${
                large ? 'top-4 right-4 px-3.5 py-2.5' : 'top-2 right-12 px-2.5 py-1.5 text-sm'
            }`}
            title="Моє місцезнаходження"
        >
            {locating ? '...' : (
                <svg width={large ? 28 : 18} height={large ? 28 : 18} viewBox="0 0 24 24">
                    <defs>
                        <clipPath id="geo-pin">
                            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
                        </clipPath>
                    </defs>
                    <g clipPath="url(#geo-pin)">
                        <rect x="0" y="0" width="24" height="12" fill="#2980B9"/>
                        <rect x="0" y="12" width="24" height="12" fill="#F1C410"/>
                    </g>
                    <circle cx="12" cy="9" r="2.5" fill="white"/>
                </svg>
            )}
        </button>
    );
}

function InvalidateSize() {
    const map = useMap();
    useEffect(() => {
        setTimeout(() => map.invalidateSize(), 100);
    }, [map]);
    return null;
}

export default function LocationPicker({value, onChange, error}: LocationPickerProps) {
    const [fullscreen, setFullscreen] = useState(false);
    const [flyKey, setFlyKey] = useState(0);

    const closeFullscreen = () => {
        setFullscreen(false);
        setFlyKey(k => k + 1);
    };

    return (
        <div>
            <div className="relative h-64 rounded-lg overflow-hidden border border-gray-200">
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
                    <LocateMe onLocate={onChange}/>
                    {value && <Marker position={[value.latitude, value.longitude]}/>}
                    <FlyToValue value={value} flyKey={flyKey}/>
                </MapContainer>
                <button
                    type="button"
                    onClick={() => setFullscreen(true)}
                    className="absolute top-2 right-2 z-[1000] bg-white border border-gray-300 rounded-lg px-2.5 py-1.5 text-sm text-gray-700 hover:bg-gray-50 shadow-sm cursor-pointer"
                    title="Розгорнути карту"
                >
                    ⛶
                </button>
            </div>

            <p className="text-sm mt-1.5 text-gray-500">
                {value
                    ? `${value.latitude.toFixed(6)}, ${value.longitude.toFixed(6)}`
                    : 'Натисніть на карту, щоб обрати місцезнаходження'
                }
            </p>
            {error && <p className="text-red-600 text-sm mt-1">{error}</p>}

            {/* Fullscreen overlay */}
            {fullscreen && (
                <div className="fixed inset-0 z-[9999] bg-white flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200">
                        <span className="text-sm text-gray-600">
                            {value
                                ? `${value.latitude.toFixed(6)}, ${value.longitude.toFixed(6)}`
                                : 'Натисніть на карту, щоб обрати місцезнаходження'
                            }
                        </span>
                        <button
                            type="button"
                            onClick={closeFullscreen}
                            className="px-4 py-3 bg-amber-600 text-white text-sm rounded-lg hover:bg-amber-700 cursor-pointer"
                        >
                            Підтвердити
                        </button>
                    </div>
                    <div className="flex-1">
                        <MapContainer
                            center={value ? [value.latitude, value.longitude] : [49.0, 32.0]}
                            zoom={value ? 12 : 6}
                            minZoom={6}
                            maxBounds={UKRAINE_BOUNDS}
                            maxBoundsViscosity={1.0}
                            scrollWheelZoom={true}
                            className="h-full w-full"
                        >
                            <InvalidateSize/>
                            <TileLayer
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                            />
                            <ClickHandler onChange={onChange}/>
                            <LocateMe onLocate={onChange} large/>
                            {value && <Marker position={[value.latitude, value.longitude]}/>}
                        </MapContainer>
                    </div>
                </div>
            )}
        </div>
    );
}
