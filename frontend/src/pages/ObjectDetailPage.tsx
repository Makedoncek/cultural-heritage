import {useState, useEffect} from 'react';
import {useParams, useNavigate, Link} from 'react-router';
import {MapContainer, TileLayer, Marker} from 'react-leaflet';
import {objectsService} from '../services/objects.service';
import {useAuth} from '../context/AuthContext';
import type {CulturalObjectDetail} from '../types';
import '../utils/leaflet-fix';

const STATUS_LABELS: Record<string, string> = {
    pending: 'На модерації',
    approved: 'Опубліковано',
    archived: 'Архівовано',
};

const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    approved: 'bg-green-100 text-green-800',
    archived: 'bg-gray-100 text-gray-600',
};

export default function ObjectDetailPage() {
    const {id} = useParams();
    const navigate = useNavigate();
    const {user} = useAuth();
    const [object, setObject] = useState<CulturalObjectDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [notFound, setNotFound] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        if (!id) return;
        setLoading(true);
        objectsService.getById(Number(id))
            .then(data => setObject(data))
            .catch(err => {
                if (err.response?.status === 404) {
                    setNotFound(true);
                } else {
                    setError('Не вдалося завантажити об\'єкт.');
                }
            })
            .finally(() => setLoading(false));
    }, [id]);

    const canEdit = user && object && (user.username === object.author || user.is_staff);

    const handleDelete = async () => {
        if (!object || !confirm('Ви впевнені, що хочете видалити цей об\'єкт?')) return;
        setDeleting(true);
        try {
            await objectsService.delete(object.id);
            navigate('/');
        } catch {
            setError('Не вдалося видалити об\'єкт.');
            setDeleting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
                    <p className="text-gray-600">Завантаження...</p>
                </div>
            </div>
        );
    }

    if (notFound) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <p className="text-gray-600 text-lg">Об'єкт не знайдено</p>
                    <Link to="/" className="text-amber-600 hover:text-amber-800 underline">
                        На карту
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
                        Спробувати знову
                    </button>
                </div>
            </div>
        );
    }

    if (!object) return null;

    const latitude = parseFloat(object.latitude);
    const longitude = parseFloat(object.longitude);

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6">

                <div className="flex items-start justify-between gap-4 mb-4">
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-bold text-gray-900">{object.title}</h1>
                        {canEdit && (
                            <span className={`px-2 py-1 text-xs rounded flex-shrink-0 ${STATUS_COLORS[object.status]}`}>
                                {STATUS_LABELS[object.status]}
                            </span>
                        )}
                    </div>
                    {canEdit && (
                        <div className="flex gap-2 flex-shrink-0">
                            <button
                                onClick={() => navigate(`/objects/${object.id}/edit`)}
                                className="px-3 py-1.5 text-sm bg-amber-500 text-white rounded hover:bg-amber-600 cursor-pointer"
                            >
                                Редагувати
                            </button>
                            <button
                                onClick={handleDelete}
                                disabled={deleting}
                                className="px-3 py-1.5 text-sm bg-red-500 text-white rounded hover:bg-red-600 cursor-pointer disabled:opacity-50"
                            >
                                {deleting ? 'Видалення...' : 'Видалити'}
                            </button>
                        </div>
                    )}
                </div>


                {object.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                        {object.tags.map(tag => (
                            <span
                                key={tag.id}
                                className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-100 text-amber-800 rounded-full text-sm"
                            >
                                {tag.icon} {tag.name}
                            </span>
                        ))}
                    </div>
                )}


                {object.description && (
                    <div className="mb-6">
                        <p className="text-gray-700 whitespace-pre-line leading-relaxed">{object.description}</p>
                    </div>
                )}

                <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
                    <span>📍 Координати: {latitude.toFixed(6)}, {longitude.toFixed(6)}</span>
                    <button
                        onClick={() => navigator.clipboard.writeText(`${latitude.toFixed(6)}, ${longitude.toFixed(6)}`)}
                        className="px-2 py-0.5 text-xs text-amber-600 hover:text-amber-800 border border-amber-200 rounded hover:bg-amber-50 cursor-pointer"
                    >
                        Скопіювати
                    </button>
                </div>


                <div className="h-64 rounded-lg overflow-hidden border border-gray-200 mb-6">
                    <MapContainer
                        center={[latitude, longitude]}
                        zoom={13}
                        scrollWheelZoom={true}
                        dragging={true}
                        zoomControl={true}
                        className="h-full w-full"
                    >
                        <TileLayer
                            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        <Marker position={[latitude, longitude]}/>
                    </MapContainer>
                </div>

                {(object.wikipedia_url || object.official_website || object.google_maps_url) && (
                    <div className="mb-6">
                        <h2 className="text-sm font-semibold text-gray-700 mb-2">Посилання</h2>
                        <div className="flex flex-wrap gap-3">
                            {object.wikipedia_url && (
                                <a href={object.wikipedia_url} target="_blank" rel="noopener noreferrer"
                                   className="text-sm text-blue-600 hover:text-blue-800 underline">
                                    Wikipedia
                                </a>
                            )}
                            {object.official_website && (
                                <a href={object.official_website} target="_blank" rel="noopener noreferrer"
                                   className="text-sm text-blue-600 hover:text-blue-800 underline">
                                    Офіційний сайт
                                </a>
                            )}
                            {object.google_maps_url && (
                                <a href={object.google_maps_url} target="_blank" rel="noopener noreferrer"
                                   className="text-sm text-blue-600 hover:text-blue-800 underline">
                                    Google Maps
                                </a>
                            )}
                        </div>
                    </div>
                )}

                {/* Meta info */}
                <div className="border-t border-gray-200 pt-4 text-sm text-gray-500">
                    <p>Автор: {object.author}</p>
                    <p>Створено: {new Date(object.created_at).toLocaleDateString('uk-UA')}</p>
                    {new Date(object.updated_at).getTime() - new Date(object.created_at).getTime() > 60000 && (
                        <p>Оновлено: {new Date(object.updated_at).toLocaleDateString('uk-UA')}</p>
                    )}
                </div>
            </div>
        </div>
    );
}