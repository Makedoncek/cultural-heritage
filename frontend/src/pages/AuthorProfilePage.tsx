import {useState, useEffect} from 'react';
import {useParams, Link} from 'react-router';
import {MapContainer} from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import {useTranslation} from 'react-i18next';
import ObjectMarker from '../components/Map/ObjectMarker';
import ThemedTileLayer from '../components/Map/ThemedTileLayer';
import FavoriteButton from '../components/Objects/FavoriteButton';
import {usersService} from '../services/users.service';
import {useAuth} from '../context/AuthContext';
import type {AuthorProfile, CulturalObject} from '../types';
import '../utils/leaflet-fix';

export default function AuthorProfilePage() {
    const {username} = useParams<{ username: string }>();
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const {user, isAuthenticated} = useAuth();
    const [profile, setProfile] = useState<AuthorProfile | null>(null);
    const [objects, setObjects] = useState<CulturalObject[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const isOwnProfile = user?.username === username;

    useEffect(() => {
        if (!username) return;
        setLoading(true);
        setError(null);

        Promise.all([
            usersService.getProfile(username),
            usersService.getObjects(username),
        ])
            .then(([profileData, objectsData]) => {
                setProfile(profileData);
                setObjects(objectsData);
            })
            .catch(() => setError(t('profile.userNotFound')))
            .finally(() => setLoading(false));
    }, [username, t]);

    const handleFollow = async () => {
        if (!username || !profile) return;
        const result = await usersService.toggleFollow(username);
        setProfile({...profile, is_followed: result.is_followed, followers_count: result.followers_count});
    };

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
                    <p className="text-gray-600">{t('home.loading')}</p>
                </div>
            </div>
        );
    }

    if (error || !profile) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <p className="text-red-600">{error ?? t('profile.loadError')}</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                {/* Author info */}
                <div className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-5 mb-6">
                    <div className="flex items-center justify-between mb-3">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100">{profile.username}</h1>
                        {isAuthenticated && !isOwnProfile && (
                            <button
                                onClick={handleFollow}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                                    profile.is_followed
                                        ? 'bg-gray-200 dark:bg-stone-800 text-gray-700 dark:text-stone-200 hover:bg-gray-300 dark:hover:bg-stone-700'
                                        : 'bg-amber-500 hover:bg-amber-600 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900'
                                }`}
                            >
                                {profile.is_followed ? t('subscriptions.unfollow') : t('subscriptions.follow')}
                            </button>
                        )}
                        {isOwnProfile && (
                            <span className="px-3 py-1 text-xs font-medium rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300">
                                {t('profile.yourProfile')}
                            </span>
                        )}
                    </div>
                    <p className="text-gray-500 dark:text-stone-400 text-sm mb-1">
                        {t('profile.onPlatformSince', {date: new Date(profile.date_joined).toLocaleDateString(dateLocale)})}
                    </p>
                    {isOwnProfile && profile.email && (
                        <p className="text-gray-500 dark:text-stone-400 text-sm mb-3">
                            📧 <span className="text-gray-700 dark:text-stone-200">{profile.email}</span>
                        </p>
                    )}
                    <div className="flex gap-6 text-sm">
                        <div>
                            <span className="font-semibold text-gray-900 dark:text-stone-100">{profile.approved_objects_count}</span>
                            <span className="text-gray-500 dark:text-stone-400 ml-1">{t('profile.objectsCount')}</span>
                        </div>
                        <div>
                            <span className="font-semibold text-gray-900 dark:text-stone-100">{profile.total_favorites_received}</span>
                            <span className="text-gray-500 dark:text-stone-400 ml-1">{t('profile.likesCount')}</span>
                        </div>
                        <div>
                            <span className="font-semibold text-gray-900 dark:text-stone-100">{profile.followers_count}</span>
                            <span className="text-gray-500 dark:text-stone-400 ml-1">{t('profile.followersCount')}</span>
                        </div>
                    </div>
                    <div className="mt-3">
                        <Link
                            to={`/authors/${profile.username}/passport`}
                            className="inline-flex items-center gap-1 text-sm text-amber-700 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 hover:underline"
                        >
                            🎒 Переглянути культурний паспорт →
                        </Link>
                    </div>
                </div>

                {/* Map */}
                {objects.length > 0 && (
                    <div className="h-80 rounded-lg overflow-hidden border border-gray-200 dark:border-stone-700 mb-6">
                        <MapContainer
                            center={[49.0, 32.0]}
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
                )}

                {/* Objects list */}
                <h2 className="text-lg font-semibold text-gray-900 dark:text-stone-100 mb-3">
                    {t('profile.authorObjects')}
                </h2>
                {objects.length === 0 ? (
                    <p className="text-gray-500 dark:text-stone-400 text-center py-8">{t('profile.noPublishedObjects')}</p>
                ) : (
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
                                            <span>{obj.tags.map(t => t.icon).join(' ')}</span>
                                        )}
                                        <span>❤️ {obj.favorites_count ?? 0}</span>
                                    </div>
                                </div>
                                <div className="flex gap-2 flex-wrap shrink-0">
                                    {isAuthenticated && (
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
                )}
            </div>
        </div>
    );
}
