import {TileLayer} from 'react-leaflet';
import {useTheme} from '../../context/ThemeContext';

const LIGHT_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const LIGHT_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

const DARK_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const DARK_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

/**
 * Swaps OSM (light) ↔ CartoDB Dark Matter tiles based on current theme.
 * `key={theme}` forces Leaflet to re-mount the tile layer instead of trying to
 * patch URLs in place (which leaves the old tile cache on screen briefly).
 */
export default function ThemedTileLayer() {
    const {theme} = useTheme();
    const isDark = theme === 'dark';
    return (
        <TileLayer
            key={theme}
            attribution={isDark ? DARK_ATTR : LIGHT_ATTR}
            url={isDark ? DARK_URL : LIGHT_URL}
        />
    );
}
