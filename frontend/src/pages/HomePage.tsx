import {useState, useEffect, useCallback} from 'react';
import {objectsService} from '../services/objects.service';
import MapView from '../components/Map/MapView';
import ErrorBoundary from '../components/Layout/ErrorBoundary';
import type {CulturalObject} from '../types';

export default function HomePage() {
    const [objects, setObjects] = useState<CulturalObject[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchAllObjects = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const allObjects: CulturalObject[] = [];
            let page = 1;
            let hasNext = true;

            while (hasNext) {
                const response = await objectsService.getAll({page});
                allObjects.push(...response.results);
                hasNext = response.next !== null;
                page++;
            }

            setObjects(allObjects);
        } catch {
            setError('Не вдалося завантажити культурні об\'єкти.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAllObjects();
    }, [fetchAllObjects]);

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
                <div className="flex flex-col items-center gap-4">
                    <p className="text-red-600">{error}</p>
                    <button
                        onClick={fetchAllObjects}
                        className="px-4 py-2 bg-amber-500 text-white rounded hover:bg-amber-600 cursor-pointer"
                    >
                        Спробувати знову
                    </button>
                </div>
            </div>
        );
    }

    if (objects.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <p className="text-gray-600">Культурних об'єктів не знайдено</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col flex-1">
            <div className="relative flex-1">
                <ErrorBoundary>
                    <MapView objects={objects}/>
                </ErrorBoundary>
            </div>
        </div>
    );
}