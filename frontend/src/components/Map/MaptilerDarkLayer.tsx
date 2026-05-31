import {useEffect} from 'react';
import {useMap} from 'react-leaflet';
import {MaptilerLayer} from '@maptiler/leaflet-maptilersdk';
import '@maptiler/sdk/dist/maptiler-sdk.css';
import type {Layer} from 'leaflet';

interface MaptilerDarkLayerProps {
    apiKey: string;
    styleId: string;
}

/**
 * Dark basemap rendered as MapTiler vector tiles (MapLibre GL) on a canvas beneath
 * Leaflet's marker/cluster panes — the MapTiler plan in use blocks raster tiles.
 * This whole module is imported lazily (see ThemedTileLayer), so MapLibre GL (~1MB)
 * and its CSS only ship once the user switches to the dark theme.
 */
export default function MaptilerDarkLayer({apiKey, styleId}: Readonly<MaptilerDarkLayerProps>) {
    const map = useMap();

    useEffect(() => {
        // Cap at 19 so the dark theme shares the same maximum zoom as the light
        // (raster OSM) layer; restore the previous limit when the layer unmounts.
        const prevMaxZoom = map.getMaxZoom();
        map.setMaxZoom(19);

        // language: 'uk' forces Ukrainian labels regardless of the style's default.
        const layer: Layer = new MaptilerLayer({apiKey, style: styleId, language: 'uk'});
        layer.addTo(map);

        return () => {
            map.removeLayer(layer);
            map.setMaxZoom(prevMaxZoom);
        };
    }, [map, apiKey, styleId]);

    return null;
}
