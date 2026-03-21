import {useState, useEffect} from 'react';
import {Link} from 'react-router';
import {objectsService} from '../services/objects.service';
import type {CulturalObject} from '../types';

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

export default function MyObjectsPage() {
    const [objects, setObjects] = useState<CulturalObject[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        objectsService.getMy()
            .then(data => setObjects(data.results))
            .catch(() => setError('Не вдалося завантажити об\'єкти.'))
            .finally(() => setLoading(false));
    }, []);

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
                <div className="flex items-center justify-between mb-6">
                    <h1 className="text-2xl font-bold text-gray-900">Мої об'єкти</h1>
                    <Link
                        to="/objects/add"
                        className="px-4 py-2 bg-amber-600 text-white text-sm rounded-lg hover:bg-amber-700"
                    >
                        Додати
                    </Link>
                </div>

                {objects.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500 mb-4">У вас ще немає доданих об'єктів</p>
                        <Link
                            to="/objects/add"
                            className="text-amber-600 hover:text-amber-800 underline"
                        >
                            Додати перший об'єкт
                        </Link>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {objects.map(obj => (
                            <div
                                key={obj.id}
                                className="flex items-center justify-between border border-gray-200 rounded-lg px-4 py-3"
                            >
                                <div className="flex items-center gap-3 min-w-0">
                                    <span className="text-gray-900 font-medium truncate">{obj.title}</span>
                                    <span className={`shrink-0 px-2.5 py-0.5 text-xs font-medium rounded ${STATUS_COLORS[obj.status]}`}>
                                        {STATUS_LABELS[obj.status]}
                                    </span>
                                </div>
                                <div className="flex gap-2 shrink-0 ml-3">
                                    <Link
                                        to={`/objects/${obj.id}`}
                                        className="px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600"
                                    >
                                        Переглянути
                                    </Link>
                                    <Link
                                        to={`/objects/${obj.id}/edit`}
                                        className="px-3 py-1.5 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100"
                                    >
                                        Редагувати
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
