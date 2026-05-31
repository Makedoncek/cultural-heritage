import {TileLayer} from 'react-leaflet';
import {useTheme} from '../../context/ThemeContext';

// Light: standard OSM (free, no key)
const LIGHT_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const LIGHT_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

// Dark: MapTiler OpenStreetMap Dark (rich OSM detail with night palette) — needs API key.
// Fallback: CartoDB Dark Matter (no key, but more minimalist) when VITE_MAPTILER_KEY is absent.
const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY as string | undefined;

const DARK_URL = MAPTILER_KEY
    ? `https://api.maptiler.com/maps/openstreetmap-dark/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`
    : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';

const DARK_ATTR = MAPTILER_KEY
    ? '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

/**
 * Swaps OSM (light) ↔ MapTiler OSM-Dark tiles based on current theme.
 * `key={theme}` forces Leaflet to re-mount the tile layer instead of trying to
 * patch URLs in place (which leaves the old tile cache on screen briefly).
 */
export default function ThemedTileLayer() {
    const {theme} = useTheme();
    const isDark = theme === 'dark';
    // MapTiler serves 512px raster tiles; OSM and the CartoDB fallback serve 256px.
    // Declaring tileSize/zoomOffset for MapTiler keeps the dark layer's scale and
    // maximum zoom identical to the light layer instead of rendering one level closer.
    const isMapTiler = isDark && !!MAPTILER_KEY;
    return (
        <TileLayer
            key={theme}
            attribution={isDark ? DARK_ATTR : LIGHT_ATTR}
            url={isDark ? DARK_URL : LIGHT_URL}
            maxZoom={19}
            tileSize={isMapTiler ? 512 : 256}
            zoomOffset={isMapTiler ? -1 : 0}
        />
    );
}
