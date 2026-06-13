import {memo} from 'react';
import {MapContainer} from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import ObjectMarker from '../Map/ObjectMarker';
import ThemedTileLayer from '../Map/ThemedTileLayer';
import type {MapCulturalObject} from '../../types';

interface Props {
    objects: MapCulturalObject[];
}

// Memoized: the author's full point-set is loaded once and never changes while
// the list pages in, so "Load more" re-renders must not touch the map.
function AuthorObjectsMap({objects}: Readonly<Props>) {
    return (
        <div className="h-80 rounded-lg overflow-hidden border border-gray-200 dark:border-stone-700 mb-6">
            <MapContainer
                center={[49, 32]}
                zoom={6}
                scrollWheelZoom={true}
                className="h-full w-full"
            >
                <ThemedTileLayer/>
                <MarkerClusterGroup chunkedLoading>
                    {objects.map(obj => (
                        <ObjectMarker key={obj.id} object={obj}/>
                    ))}
                </MarkerClusterGroup>
            </MapContainer>
        </div>
    );
}

export default memo(AuthorObjectsMap);
