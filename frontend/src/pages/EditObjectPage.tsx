import {useState, useEffect} from 'react';
import {useParams, useNavigate, Link} from 'react-router';
import {objectsService} from '../services/objects.service';
import {useAuth} from '../context/AuthContext';
import ObjectForm from '../components/Objects/ObjectForm';
import type {CulturalObjectDetail, CulturalObjectWrite, ObjectFormData} from '../types';

function detailToFormData(obj: CulturalObjectDetail): ObjectFormData {
    return {
        title: obj.title,
        description: obj.description,
        tags: obj.tags.map(t => t.id),
        latitude: parseFloat(obj.latitude),
        longitude: parseFloat(obj.longitude),
        wikipedia_url: obj.wikipedia_url || '',
        official_website: obj.official_website || '',
        google_maps_url: obj.google_maps_url || '',
    };
}

export default function EditObjectPage() {
    const {id} = useParams();
    const navigate = useNavigate();
    const {user} = useAuth();
    const [object, setObject] = useState<CulturalObjectDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [notFound, setNotFound] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;
        objectsService.getById(Number(id))
            .then(data => {
                if (user && (user.username === data.author || user.is_staff)) {
                    setObject(data);
                } else {
                    setError('У вас немає прав для редагування цього об\'єкта.');
                }
            })
            .catch(err => {
                if (err.response?.status === 404) setNotFound(true);
                else setError('Не вдалося завантажити об\'єкт.');
            })
            .finally(() => setLoading(false));
    }, [id, user]);

    const handleSubmit = async (data: CulturalObjectWrite) => {
        await objectsService.update(Number(id), data);
        navigate(`/objects/${id}`);
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
                    <Link to="/" className="text-amber-600 hover:text-amber-800 underline">На карту</Link>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <p className="text-red-600">{error}</p>
                    <Link to="/" className="text-amber-600 hover:text-amber-800 underline">На карту</Link>
                </div>
            </div>
        );
    }

    if (!object) return null;

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-4">Редагувати об'єкт</h1>
                {object.status === 'approved' && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 mb-6">
                        <p className="text-yellow-800 text-sm">
                            Після редагування об'єкт буде відправлено на повторну модерацію
                        </p>
                    </div>
                )}
                <ObjectForm
                    initialData={detailToFormData(object)}
                    onSubmit={handleSubmit}
                    submitLabel="Зберегти"
                    submittingLabel="Збереження..."
                />
            </div>
        </div>
    );
}
