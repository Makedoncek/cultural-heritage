import {Link} from 'react-router';
import {MapContainer} from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import {useTranslation} from 'react-i18next';
import ObjectMarker from '../Map/ObjectMarker';
import ThemedTileLayer from '../Map/ThemedTileLayer';
import FavoriteButton from '../Objects/FavoriteButton';
import {useAuth} from '../../context/AuthContext';
import type {CulturalObject} from '../../types';

interface Props {
    objects: CulturalObject[];
    isAuthenticated: boolean;
}

export default function AuthorObjectsTab({objects, isAuthenticated}: Readonly<Props>) {
    const {t} = useTranslation();
    const {user} = useAuth();

    if (objects.length === 0) {
        return <p className="text-gray-500 dark:text-stone-400 text-center py-8">{t('profile.noPublishedObjects')}</p>;
    }

    return (
        <>
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

            <div className="space-y-3">
                {objects.map(obj => (
                    <div
                        key={obj.id}
                        className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                    >
                        <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="text-gray-900 dark:text-stone-100 font-medium">{obj.title}</span>
                                {obj.object_type === 'event' && (
                                    <span className="px-2 py-0.5 text-xs font-medium rounded bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-300">
                                        {t('object.objectType.event')}
                                    </span>
                                )}
                                {obj.status === 'pending' && (
                                    <span className="px-2 py-0.5 text-xs font-medium rounded bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-300">
                                        {t('object.moderationStatus.pending')}
                                    </span>
                                )}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-stone-400 mt-1">
                                {obj.tags.length > 0 && (
                                    <span>{obj.tags.map(tg => tg.icon).join(' ')}</span>
                                )}
                                <span>❤️ {obj.favorites_count ?? 0}</span>
                            </div>
                        </div>
                        <div className="flex gap-2 flex-wrap shrink-0">
                            {isAuthenticated && user?.username !== obj.author_name && (
                                <FavoriteButton
                                    objectId={obj.id}
                                    initialFavorited={obj.is_favorited ?? false}
                                    initialCount={obj.favorites_count ?? 0}
                                />
                            )}
                            <Link
                                to={`/objects/${obj.id}`}
                                className="px-3 py-1.5 text-sm bg-amber-500 hover:bg-amber-600 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg"
                            >
                                {t('myObjects.view')}
                            </Link>
                        </div>
                    </div>
                ))}
            </div>
        </>
    );
}
