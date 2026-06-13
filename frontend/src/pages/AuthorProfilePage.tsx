import {useCallback, useEffect, useMemo, useState, type ReactNode} from 'react';
import {useParams, useSearchParams} from 'react-router';
import {useTranslation} from 'react-i18next';
import {usersService} from '../services/users.service';
import {objectsService} from '../services/objects.service';
import {tagsService} from '../services/tags.service';
import {usePaginatedList} from '../hooks/usePaginatedList';
import {useAuth} from '../context/AuthContext';
import AuthorObjectsTab from '../components/Author/AuthorObjectsTab';
import AuthorVisitsTab from '../components/Author/AuthorVisitsTab';
import type {AuthorProfile, CulturalObject, MapCulturalObject, MapObjectRaw, Tag} from '../types';
import '../utils/leaflet-fix';

type Tab = 'objects' | 'visits';

export default function AuthorProfilePage() {
    const {username} = useParams<{ username: string }>();
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const {user, isAuthenticated} = useAuth();
    const [profile, setProfile] = useState<AuthorProfile | null>(null);
    const [mapRaw, setMapRaw] = useState<MapObjectRaw[]>([]);
    const [allTags, setAllTags] = useState<Tag[]>([]);
    const [profileLoading, setProfileLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [visitCount, setVisitCount] = useState<number | null>(null);

    const [params, setParams] = useSearchParams();
    const initialTab: Tab = params.get('tab') === 'visits' ? 'visits' : 'objects';
    const [tab, setTab] = useState<Tab>(initialTab);

    const isOwnProfile = user?.username === username;

    // List of the author's objects — paginated with a "Load more" button.
    const {items: listObjects, count: objectsCount, nextUrl, loading: listLoading, loadingMore, loadMore} =
        usePaginatedList<CulturalObject>({
            initialFetch: () => usersService.getObjects(username!),
            fetchByUrl: (url) => usersService.getObjectsByUrl(url),
            deps: [username, i18n.language],
        });

    // Profile + ALL map points (one lightweight request) + tag dictionary for enrichment.
    useEffect(() => {
        if (!username) return;
        setProfileLoading(true);
        setError(null);

        Promise.all([
            usersService.getProfile(username),
            objectsService.getMap({author: username}),
            tagsService.getAll(),
        ])
            .then(([profileData, mapData, tagsData]) => {
                setProfile(profileData);
                setMapRaw(mapData);
                setAllTags(tagsData.results);
            })
            .catch(() => setError(t('profile.userNotFound')))
            .finally(() => setProfileLoading(false));
    }, [username, t]);

    // Lightweight map objects carry tags as ids; enrich them from the tag dictionary.
    const mapObjects = useMemo<MapCulturalObject[]>(() => {
        const byId = new Map(allTags.map(tag => [tag.id, tag]));
        return mapRaw.map(o => ({
            ...o,
            tags: o.tags.map(id => byId.get(id)).filter((tag): tag is Tag => Boolean(tag)),
        }));
    }, [mapRaw, allTags]);

    const handleFollow = async () => {
        if (!username || !profile) return;
        const result = await usersService.toggleFollow(username);
        setProfile({...profile, is_followed: result.is_followed, followers_count: result.followers_count});
    };

    const handleTabChange = (next: Tab) => {
        setTab(next);
        setParams({tab: next}, {replace: true});
    };

    const onVisitsCount = useCallback((n: number) => setVisitCount(n), []);

    if (profileLoading || listLoading) {
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
                {/* Author info card */}
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
                </div>

                {/* Tabs */}
                <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-stone-700">
                    <TabBtn active={tab === 'objects'} onClick={() => handleTabChange('objects')} count={objectsCount}>
                        🗺 {t('profile.authorObjects')}
                    </TabBtn>
                    <TabBtn active={tab === 'visits'} onClick={() => handleTabChange('visits')} count={visitCount}>
                        🎒 {t('profile.visitsTab')}
                    </TabBtn>
                </div>

                {tab === 'objects'
                    ? <AuthorObjectsTab
                        mapObjects={mapObjects}
                        listObjects={listObjects}
                        isAuthenticated={isAuthenticated}
                        nextUrl={nextUrl}
                        loadingMore={loadingMore}
                        totalCount={objectsCount}
                        onLoadMore={loadMore}/>
                    : <AuthorVisitsTab username={profile.username} onCountChange={onVisitsCount}/>}
            </div>
        </div>
    );
}

interface TabBtnProps {
    active: boolean;
    onClick: () => void;
    count: number | null;
    children: ReactNode;
}

function TabBtn({active, onClick, count, children}: Readonly<TabBtnProps>) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors cursor-pointer ${
                active
                    ? 'border-amber-500 text-amber-700 dark:text-amber-400'
                    : 'border-transparent text-gray-500 dark:text-stone-400 hover:text-gray-700 dark:hover:text-stone-200'
            }`}
        >
            {children}
            {count !== null && (
                <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${active ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300' : 'bg-gray-100 dark:bg-stone-800 text-gray-600 dark:text-stone-400'}`}>
                    {count}
                </span>
            )}
        </button>
    );
}
