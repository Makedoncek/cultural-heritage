import {useState, useEffect} from 'react';
import {Link} from 'react-router';
import {objectsService} from '../services/objects.service';
import type {CulturalObject} from '../types';
import FavoriteButton from '../components/Objects/FavoriteButton';

export default function FavoritesPage() {
    const [objects, setObjects] = useState<CulturalObject[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchAll = async () => {
            try {
                const allObjects: CulturalObject[] = [];
                let page = 1;
                let hasNext = true;
                while (hasNext) {
                    const response = await objectsService.getFavorites({page});
                    allObjects.push(...response.results);
                    hasNext = response.next !== null;
                    page++;
                }
                setObjects(allObjects);
            } catch {
                setError('Не вдалося завантажити обране.');
            } finally {
                setLoading(false);
            }
        };
        fetchAll();
    }, []);

    const handleUnfavorited = (id: number) => {
        setObjects(prev => prev.filter(obj => obj.id !== id));
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

    if (error) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <p className="text-red-600">{error}</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-6">Обране</h1>

                {objects.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500 mb-4">У вас ще немає обраних об'єктів</p>
                        <Link to="/" className="text-amber-600 hover:text-amber-800 underline">
                            Перейти до карти
                        </Link>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {objects.map(obj => (
                            <div
                                key={obj.id}
                                className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 border border-gray-200 rounded-lg px-4 py-3"
                            >
                                <div className="min-w-0">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span className="text-gray-900 font-medium">{obj.title}</span>
                                        {obj.object_type === 'event' && (
                                            <span className="px-2 py-0.5 text-xs font-medium rounded bg-purple-100 text-purple-800">
                                                Подія
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                                        {obj.tags.length > 0 && (
                                            <span>{obj.tags.map(t => t.icon).join(' ')}</span>
                                        )}
                                        <span>{new Date(obj.created_at).toLocaleDateString('uk-UA')}</span>
                                    </div>
                                </div>
                                <div className="flex gap-2 flex-wrap shrink-0">
                                    <FavoriteButton
                                        objectId={obj.id}
                                        initialFavorited={true}
                                        initialCount={obj.favorites_count ?? 0}
                                        onToggle={(favorited) => { if (!favorited) handleUnfavorited(obj.id); }}
                                    />
                                    <Link
                                        to={`/objects/${obj.id}`}
                                        className="px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600"
                                    >
                                        Переглянути
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
