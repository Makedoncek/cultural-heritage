import {lazy, Suspense} from 'react';
import {TileLayer} from 'react-leaflet';
import {useTranslation} from 'react-i18next';
import {useTheme} from '../../context/ThemeContext';

// Light raster OSM and CartoDB dark are used only as the no-key fallback; with a
// MapTiler key both themes render as vector tiles whose label language follows the UI.
const LIGHT_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const LIGHT_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const CARTO_DARK_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const CARTO_DARK_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

// MapTiler vector styles: custom Ukrainian-localized dark map + built-in light OSM.
// Labels are localized at runtime by MaptilerVectorLayer, so one style serves both languages.
const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY as string | undefined;
const DARK_STYLE = (import.meta.env.VITE_MAPTILER_DARK_STYLE as string | undefined)
    || '019e7f53-ec26-7a6f-a938-f79351a82b04';
const LIGHT_STYLE = (import.meta.env.VITE_MAPTILER_LIGHT_STYLE as string | undefined)
    || '019e7f81-ffb9-7dca-86a6-b86f25c1ac33';

const MaptilerVectorLayer = lazy(() => import('./MaptilerVectorLayer'));

/**
 * Selects the basemap for the current theme and UI language. With a MapTiler key,
 * both themes use vector tiles (label language follows i18n); without one, it falls
 * back to raster OSM (light) / CartoDB (dark). `key={theme}` re-mounts the raster
 * fallback so stale tiles don't linger on switch.
 */
export default function ThemedTileLayer() {
    const {theme} = useTheme();
    const {i18n} = useTranslation();
    const isDark = theme === 'dark';
    const language = i18n.resolvedLanguage?.startsWith('en') ? 'en' : 'uk';

    if (MAPTILER_KEY) {
        return (
            <Suspense fallback={null}>
                <MaptilerVectorLayer
                    apiKey={MAPTILER_KEY}
                    styleId={isDark ? DARK_STYLE : LIGHT_STYLE}
                    language={language}
                />
            </Suspense>
        );
    }

    return (
        <TileLayer
            key={theme}
            attribution={isDark ? CARTO_DARK_ATTR : LIGHT_ATTR}
            url={isDark ? CARTO_DARK_URL : LIGHT_URL}
            maxZoom={19}
        />
    );
}
