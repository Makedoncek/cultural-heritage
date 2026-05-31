import {useEffect, useRef} from 'react';
import {useMap} from 'react-leaflet';
import {MaptilerLayer} from '@maptiler/leaflet-maptilersdk';
import '@maptiler/sdk/dist/maptiler-sdk.css';

interface MaptilerVectorLayerProps {
    apiKey: string;
    styleId: string;
    language: string;
}

/**
 * Basemap rendered as MapTiler vector tiles (MapLibre GL) on a canvas beneath
 * Leaflet's marker/cluster panes — the MapTiler plan in use blocks raster tiles.
 * This whole module is imported lazily (see ThemedTileLayer), so MapLibre GL (~1MB)
 * and its CSS only ship once a map with a MapTiler key is shown.
 *
 * The style is swapped per theme (light/dark); the label language is updated in
 * place via setLanguage so switching uk↔en doesn't rebuild the GL context.
 */
export default function MaptilerVectorLayer({apiKey, styleId, language}: Readonly<MaptilerVectorLayerProps>) {
    const map = useMap();
    const layerRef = useRef<InstanceType<typeof MaptilerLayer> | null>(null);

    // Create/replace the layer when the style (theme) changes; language is passed
    // up front so a freshly-built layer already renders the correct language.
    // (maxZoom is set on each MapContainer, which markercluster requires at init.)
    useEffect(() => {
        const layer = new MaptilerLayer({apiKey, style: styleId, language});
        layer.addTo(map);
        layerRef.current = layer;

        return () => {
            map.removeLayer(layer);
            layerRef.current = null;
        };
    }, [map, apiKey, styleId]);

    // Update labels in place when only the app language changes.
    useEffect(() => {
        layerRef.current?.setLanguage(language);
    }, [language]);

    return null;
}
