import {lazy, Suspense} from 'react';
import {TileLayer} from 'react-leaflet';
import {useTheme} from '../../context/ThemeContext';

// Light: standard OSM raster (free, no key) — already renders local Ukrainian names.
const LIGHT_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const LIGHT_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

// Dark: MapTiler vector tiles via a custom Ukrainian-localized map (the raster tile
// API is unavailable on the current MapTiler plan). VITE_MAPTILER_DARK_STYLE is the
// custom map id; the vector engine is loaded lazily (see MaptilerDarkLayer).
// Fallback: CartoDB Dark Matter raster (no key, more minimalist) when no key is set.
const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY as string | undefined;
const MAPTILER_DARK_STYLE = (import.meta.env.VITE_MAPTILER_DARK_STYLE as string | undefined)
    || '019e7f53-ec26-7a6f-a938-f79351a82b04';

const CARTO_DARK_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const CARTO_DARK_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

const MaptilerDarkLayer = lazy(() => import('./MaptilerDarkLayer'));

/**
 * Picks the basemap for the current theme: raster OSM (light), MapTiler vector tiles
 * (dark, when a key is configured), or the CartoDB raster fallback (dark, no key).
 * `key={theme}` re-mounts the raster layer so stale tiles don't linger on switch.
 */
export default function ThemedTileLayer() {
    const {theme} = useTheme();

    if (theme === 'dark' && MAPTILER_KEY) {
        return (
            <Suspense fallback={null}>
                <MaptilerDarkLayer apiKey={MAPTILER_KEY} styleId={MAPTILER_DARK_STYLE}/>
            </Suspense>
        );
    }

    const isDark = theme === 'dark';
    return (
        <TileLayer
            key={theme}
            attribution={isDark ? CARTO_DARK_ATTR : LIGHT_ATTR}
            url={isDark ? CARTO_DARK_URL : LIGHT_URL}
            maxZoom={19}
        />
    );
}
