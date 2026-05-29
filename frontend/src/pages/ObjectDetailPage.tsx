import {useState, useEffect} from 'react';
import {useParams, useNavigate, Link} from 'react-router';
import {MapContainer, Marker} from 'react-leaflet';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import ThemedTileLayer from '../components/Map/ThemedTileLayer';
import {objectsService} from '../services/objects.service';
import {photosService, extractUploadError} from '../services/photos.service';
import {useAuth} from '../context/AuthContext';
import FavoriteButton from '../components/Objects/FavoriteButton';
import VisitedToggleButton from '../components/Objects/VisitedToggleButton';
import PlanVisitToggleButton from '../components/Objects/PlanVisitToggleButton';
import PhotoGallery from '../components/Objects/PhotoGallery';
import PhotoUploader, {type PendingPhoto} from '../components/Objects/PhotoUploader';
import ReportInaccuracyButton from '../components/Objects/ReportInaccuracyButton';
import AddToRouteButton from '../components/Objects/AddToRouteButton';
import AudioGuidesSection from '../components/Audio/AudioGuidesSection';
import ContentLanguageSelector, {type ContentLanguage} from '../components/Translation/ContentLanguageSelector';
import TranslationSubmitModal from '../components/Translation/TranslationSubmitModal';
import type {CulturalObjectDetail} from '../types';
import '../utils/leaflet-fix';

const ALL_CONTENT_LANGUAGES: ContentLanguage[] = ['uk', 'en', 'pl', 'de'];

const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    approved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    archived: 'bg-gray-100 text-gray-600 dark:bg-stone-800 dark:text-stone-400',
};

export default function ObjectDetailPage() {
    const {id} = useParams();
    const navigate = useNavigate();
    const {t, i18n} = useTranslation();
    const {user, isAuthenticated} = useAuth();
    const [object, setObject] = useState<CulturalObjectDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [notFound, setNotFound] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [deleting, setDeleting] = useState(false);
    const [contribPhotos, setContribPhotos] = useState<PendingPhoto[]>([]);
    const [uploadingContrib, setUploadingContrib] = useState(false);
    const [contribProgress, setContribProgress] = useState({done: 0, total: 0});
    const [showContribUploader, setShowContribUploader] = useState(false);
    const [showTranslationModal, setShowTranslationModal] = useState(false);
    const [contentLang, setContentLang] = useState<ContentLanguage | null>(null);

    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';

    useEffect(() => {
        if (!id) return;
        setLoading(true);
        objectsService.getById(Number(id))
            .then(data => {
                setObject(data);
                const uiLang = (i18n.resolvedLanguage || 'uk') as ContentLanguage;
                setContentLang(data.available_languages.includes(uiLang) ? uiLang : data.original_language);
            })
            .catch(err => {
                if (err.response?.status === 404) {
                    setNotFound(true);
                } else {
                    setError(t('object.loadError'));
                }
            })
            .finally(() => setLoading(false));
    }, [id, t]);

    const handleSelectContentLang = (lang: ContentLanguage) => {
        if (!id || lang === contentLang) return;
        setContentLang(lang);
        objectsService.getById(Number(id), lang)
            .then(setObject)
            .catch(() => toast.error(t('object.loadError')));
    };

    const canEdit = user && object && (user.username === object.author || user.is_staff);
    const isAuthor = user && object && user.username === object.author;
    const canContribute = isAuthenticated && !isAuthor && object?.status === 'approved';

    const handleContribUpload = async () => {
        if (!object || contribPhotos.length === 0) return;
        setUploadingContrib(true);
        setContribProgress({done: 0, total: contribPhotos.length});
        const failures: {name: string; reason: string}[] = [];
        for (const p of contribPhotos) {
            try {
                await photosService.upload(object.id, p.file, p.caption);
                setContribProgress(prev => ({...prev, done: prev.done + 1}));
            } catch (e) {
                failures.push({name: p.file.name, reason: extractUploadError(e)});
            }
        }
        setUploadingContrib(false);
        if (failures.length === 0) {
            toast.success(t('photo.sentForReview'));
            setContribPhotos([]);
            setShowContribUploader(false);
        } else {
            const message = failures.map(f => `«${f.name}»: ${f.reason}`).join('\n');
            toast.error(message, {duration: 6000});
        }
    };

    const handleDelete = async () => {
        if (!object || !confirm(t('object.deleteConfirm'))) return;
        setDeleting(true);
        try {
            await objectsService.delete(object.id);
            toast.success(t('object.archived'));
            navigate('/');
        } catch {
            setError(t('object.deleteError'));
            setDeleting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
                    <p className="text-gray-600 dark:text-stone-300">{t('home.loading')}</p>
                </div>
            </div>
        );
    }

    if (notFound) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <p className="text-gray-600 dark:text-stone-300 text-lg">{t('object.notFound')}</p>
                    <Link to="/" className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 underline">
                        {t('object.backToMap')}
                    </Link>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <p className="text-red-600">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-amber-500 text-white rounded hover:bg-amber-600 cursor-pointer"
                    >
                        {t('home.retry')}
                    </button>
                </div>
            </div>
        );
    }

    if (!object) return null;

    const latitude = Number.parseFloat(object.latitude);
    const longitude = Number.parseFloat(object.longitude);

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6">

                <ContentLanguageSelector
                    available={object.available_languages}
                    selected={contentLang ?? object.original_language}
                    onSelect={handleSelectContentLang}
                    onSuggest={isAuthenticated ? () => setShowTranslationModal(true) : undefined}
                />
                {isAuthenticated && object.current_translation_id && (
                    <div className="-mt-1 mb-3">
                        <ReportInaccuracyButton
                            targetType="object_translation"
                            targetId={object.current_translation_id}
                            targetTitle={object.title}
                            compact
                        />
                    </div>
                )}

                <div className="mb-4">
                    <div className="flex flex-wrap items-center gap-3 mb-2">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100">{object.title}</h1>
                        {canEdit && (
                            <span className={`px-3 py-1 text-sm font-medium rounded ${STATUS_COLORS[object.status]}`}>
                                {t(`object.moderationStatus.${object.status}`)}
                            </span>
                        )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {isAuthenticated && (
                            <>
                                {!isAuthor && (
                                    <FavoriteButton
                                        objectId={object.id}
                                        initialFavorited={object.is_favorited ?? false}
                                        initialCount={object.favorites_count ?? 0}
                                    />
                                )}
                                {!isAuthor && object.status === 'approved' && (
                                    <>
                                        <VisitedToggleButton
                                            objectId={object.id}
                                            initialVisited={object.is_visited ?? false}
                                        />
                                        <PlanVisitToggleButton
                                            objectId={object.id}
                                            initialPlanned={object.is_planned ?? false}
                                        />
                                    </>
                                )}
                                {(object.status === 'approved' || isAuthor) && object.status !== 'archived' && (
                                    <AddToRouteButton objectId={object.id}/>
                                )}
                            </>
                        )}
                        {canEdit && (
                            <>
                                <button
                                    onClick={() => navigate(`/objects/${object.id}/edit`)}
                                    className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400 text-white rounded-lg cursor-pointer"
                                >
                                    {t('object.edit')}
                                </button>
                                <button
                                    onClick={handleDelete}
                                    disabled={deleting}
                                    className="px-3 py-1.5 text-sm bg-stone-200 hover:bg-stone-300 dark:bg-stone-700 dark:hover:bg-stone-600 text-stone-700 dark:text-stone-200 rounded-lg cursor-pointer disabled:opacity-50"
                                >
                                    {deleting ? t('object.deleting') : `📦 ${t('object.delete')}`}
                                </button>
                            </>
                        )}
                    </div>
                </div>


                {object.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                        {object.tags.map(tag => (
                            <span
                                key={tag.id}
                                className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded-full text-sm"
                            >
                                {tag.icon} {tag.name}
                            </span>
                        ))}
                    </div>
                )}


                {object.object_type === 'event' && (
                    <div className="flex flex-wrap items-center gap-2 mb-4">
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-300 rounded-full text-sm font-medium">
                            🎉 {t('object.objectType.event')}
                        </span>
                        {object.event_start_date && object.event_end_date && (
                            <span className="text-sm text-gray-600 dark:text-stone-300">
                                📅 {new Date(object.event_start_date).toLocaleString(dateLocale, {day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'})} — {new Date(object.event_end_date).toLocaleString(dateLocale, {day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'})}
                            </span>
                        )}
                        {object.event_end_date && new Date(object.event_end_date) < new Date() && (
                            <span className="inline-flex items-center px-2 py-0.5 bg-gray-100 dark:bg-stone-800 text-gray-500 dark:text-stone-400 rounded-full text-xs">
                                {t('object.eventStatus.finished')}
                            </span>
                        )}
                    </div>
                )}

                {object.photos && object.photos.length > 0 && (
                    <div className="my-6">
                        <PhotoGallery photos={object.photos}/>
                    </div>
                )}

                {canContribute && (
                    <div className="my-6 p-4 border border-blue-200 dark:border-blue-800 rounded bg-blue-50 dark:bg-blue-950/40">
                        <h3 className="font-semibold mb-2 text-gray-900 dark:text-stone-100">{t('photo.addContribute')}</h3>
                        <p className="text-sm text-gray-600 dark:text-stone-300 mb-3">
                            {t('photo.contributeHint', {count: 3})}
                        </p>
                        {!showContribUploader ? (
                            <button
                                onClick={() => setShowContribUploader(true)}
                                className="px-4 py-2 bg-blue-600 text-white rounded cursor-pointer"
                            >
                                {t('photo.addPhoto')}
                            </button>
                        ) : (
                            <>
                                <PhotoUploader photos={contribPhotos} onChange={setContribPhotos} maxCount={3}/>
                                {uploadingContrib && contribProgress.total > 0 && (
                                    <div className="mt-3">
                                        <div className="flex justify-between text-xs text-gray-600 dark:text-stone-300 mb-1">
                                            <span>{t('photo.sending')}</span>
                                            <span>{contribProgress.done} / {contribProgress.total}</span>
                                        </div>
                                        <div className="w-full bg-gray-200 dark:bg-stone-700 rounded-full h-2 overflow-hidden">
                                            <div
                                                className="bg-blue-600 h-2 transition-all duration-300"
                                                style={{width: `${(contribProgress.done / contribProgress.total) * 100}%`}}
                                            />
                                        </div>
                                    </div>
                                )}
                                <div className="mt-3 flex gap-2">
                                    <button
                                        onClick={handleContribUpload}
                                        disabled={contribPhotos.length === 0 || uploadingContrib}
                                        className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50 cursor-pointer"
                                    >
                                        {uploadingContrib ? `${contribProgress.done}/${contribProgress.total}` : t('photo.send')}
                                    </button>
                                    <button
                                        onClick={() => {
                                            setShowContribUploader(false);
                                            setContribPhotos([]);
                                        }}
                                        disabled={uploadingContrib}
                                        className="px-4 py-2 border border-gray-300 dark:border-stone-600 text-gray-700 dark:text-stone-200 rounded cursor-pointer disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-stone-800"
                                    >
                                        {t('form.cancel')}
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                )}

                {object.description && (
                    <section className="my-6 bg-white dark:bg-stone-900 border border-gray-200 dark:border-stone-700 rounded-xl overflow-hidden shadow-sm">
                        <header className="flex items-center gap-2 px-5 py-2.5 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800/50">
                            <span className="text-amber-700 dark:text-amber-400">📖</span>
                            <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-300 uppercase tracking-wide">
                                {t('object.about')}
                            </h3>
                        </header>
                        <div className="px-5 py-4">
                            <p className="text-[15px] text-gray-800 dark:text-stone-100 whitespace-pre-line leading-relaxed">
                                {object.description}
                            </p>
                        </div>
                    </section>
                )}

                {object.status === 'approved' && (
                    <AudioGuidesSection
                        objectId={object.id}
                        objectTitle={object.title}
                        coverUrl={object.photos?.[0]?.image_url ?? null}
                    />
                )}

                {typeof object.visits_count === 'number' && object.visits_count > 0 && (
                    <p className="text-sm text-gray-500 dark:text-stone-400 mb-2">
                        ✓ Відвідано: <strong className="text-green-700 dark:text-green-400">{object.visits_count}</strong> {object.visits_count === 1 ? 'раз' : 'раз(ів)'}
                    </p>
                )}

                <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500 dark:text-stone-400 mb-2">
                    <span>{t('object.coordinates')} {latitude.toFixed(6)}, {longitude.toFixed(6)}</span>
                    <button
                        onClick={() => navigator.clipboard.writeText(`${latitude.toFixed(6)}, ${longitude.toFixed(6)}`)}
                        className="px-2 py-0.5 text-xs text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 border border-amber-200 dark:border-stone-600 rounded hover:bg-amber-50 dark:hover:bg-stone-800 cursor-pointer"
                    >
                        {t('object.copy')}
                    </button>
                </div>


                <div className="h-64 rounded-lg overflow-hidden border border-gray-200 dark:border-stone-700 mb-6">
                    <MapContainer
                        center={[latitude, longitude]}
                        zoom={13}
                        scrollWheelZoom={true}
                        dragging={true}
                        zoomControl={true}
                        className="h-full w-full"
                    >
                        <ThemedTileLayer/>
                        <Marker position={[latitude, longitude]}/>
                    </MapContainer>
                </div>

                {(object.wikipedia_url || object.official_website || object.google_maps_url) && (
                    <div className="mb-6">
                        <h2 className="text-sm font-semibold text-gray-700 dark:text-stone-200 mb-2">{t('object.links')}</h2>
                        <div className="flex flex-wrap gap-3">
                            {object.wikipedia_url && (
                                <a href={object.wikipedia_url} target="_blank" rel="noopener noreferrer"
                                   className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline">
                                    {t('object.wikipedia')}
                                </a>
                            )}
                            {object.official_website && (
                                <a href={object.official_website} target="_blank" rel="noopener noreferrer"
                                   className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline">
                                    {t('object.officialSite')}
                                </a>
                            )}
                            {object.google_maps_url && (
                                <a href={object.google_maps_url} target="_blank" rel="noopener noreferrer"
                                   className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline">
                                    {t('object.googleMaps')}
                                </a>
                            )}
                        </div>
                    </div>
                )}

                {/* Meta info */}
                <div className="border-t border-gray-200 dark:border-stone-700 pt-4 text-sm text-gray-500 dark:text-stone-400">
                    <p>{t('object.author')} <Link to={`/authors/${object.author}`} className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 underline">{object.author}</Link></p>
                    <p>{t('object.createdAt')} {new Date(object.created_at).toLocaleDateString(dateLocale)}</p>
                    {new Date(object.updated_at).getTime() - new Date(object.created_at).getTime() > 60000 && (
                        <p>{t('object.updatedAt')} {new Date(object.updated_at).toLocaleDateString(dateLocale)}</p>
                    )}
                    {!isAuthor && (
                        <div className="mt-3">
                            <ReportInaccuracyButton targetType="object" targetId={object.id} targetTitle={object.title}/>
                        </div>
                    )}
                </div>
            </div>

            <TranslationSubmitModal
                open={showTranslationModal}
                onClose={() => setShowTranslationModal(false)}
                targetOptions={ALL_CONTENT_LANGUAGES}
                originalLanguage={object.original_language}
                onSubmit={async payload => {
                    await objectsService.submitTranslation(object.id, payload);
                }}
            />
        </div>
    );
}
