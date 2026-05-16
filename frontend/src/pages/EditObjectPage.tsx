import {useState, useEffect} from 'react';
import {useParams, useNavigate, Link} from 'react-router';
import toast from 'react-hot-toast';
import {objectsService} from '../services/objects.service';
import {photosService, extractUploadError} from '../services/photos.service';
import {useAuth} from '../context/AuthContext';
import ObjectForm from '../components/Objects/ObjectForm';
import ExistingPhotosManager from '../components/Objects/ExistingPhotosManager';
import PhotoUploader, {type PendingPhoto} from '../components/Objects/PhotoUploader';
import type {CulturalObjectDetail, CulturalObjectWrite, ObjectFormData, ObjectPhoto} from '../types';

const MAX_AUTHOR_PHOTOS = 5;

function toDatetimeLocal(iso: string | null): string {
    if (!iso) return '';
    return iso.slice(0, 16);
}

function detailToFormData(obj: CulturalObjectDetail): ObjectFormData {
    return {
        title: obj.title,
        description: obj.description,
        tags: obj.tags.map(t => t.id),
        object_type: obj.object_type,
        event_start_date: toDatetimeLocal(obj.event_start_date),
        event_end_date: toDatetimeLocal(obj.event_end_date),
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
    const [photos, setPhotos] = useState<ObjectPhoto[]>([]);
    const [newPhotos, setNewPhotos] = useState<PendingPhoto[]>([]);
    const [loading, setLoading] = useState(true);
    const [notFound, setNotFound] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState({done: 0, total: 0});

    useEffect(() => {
        if (!id) return;
        objectsService.getById(Number(id))
            .then(data => {
                if (user && (user.username === data.author || user.is_staff)) {
                    setObject(data);
                    setPhotos(data.photos || []);
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
        const beforeStatus = object?.status;
        const updated = await objectsService.update(Number(id), data);
        const sentToModeration = beforeStatus === 'approved' && updated.status === 'pending';
        const savedMsg = sentToModeration
            ? 'Зміни збережено. Об\'єкт відправлено на повторну модерацію.'
            : 'Зміни збережено';

        if (newPhotos.length === 0 || !object) {
            toast.success(savedMsg);
            navigate(`/objects/${id}`);
            return;
        }

        setUploading(true);
        setUploadProgress({done: 0, total: newPhotos.length});
        const failed: {photo: PendingPhoto; reason: string}[] = [];
        // Sequential upload — щоб бекенд відхиляв надлишкові фото ДО Cloudinary
        // (інакше parallel uploads витрачають bandwidth на файли, що не пройдуть лiміт).
        for (const p of newPhotos) {
            try {
                await photosService.upload(object.id, p.file, p.caption);
                setUploadProgress(prev => ({...prev, done: prev.done + 1}));
            } catch (e) {
                failed.push({photo: p, reason: extractUploadError(e)});
            }
        }
        setUploading(false);

        if (failed.length === 0) {
            toast.success(savedMsg);
            navigate(`/objects/${id}`);
            return;
        }

        // Лишаємо непрозавантажені фото в стейті для повторної спроби
        setNewPhotos(failed.map(f => f.photo));
        const msg = failed.map(f => `«${f.photo.file.name}»: ${f.reason}`).join('\n');
        const prefix = sentToModeration
            ? 'Об\'єкт оновлено і відправлено на повторну модерацію'
            : 'Об\'єкт оновлено';
        if (failed.length === newPhotos.length) {
            toast.error(`${prefix}, але не вдалося завантажити фото:\n${msg}`, {duration: 7000});
        } else {
            toast.error(`${prefix}. Не завантажено:\n${msg}`, {duration: 7000});
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

    const authorPhotosCount = photos.filter(p => p.is_author_photo).length;
    const remainingSlots = Math.max(0, MAX_AUTHOR_PHOTOS - authorPhotosCount);

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-4">Редагувати об'єкт</h1>
                {object.status === 'approved' && !user?.is_staff && (
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
                >
                    <ExistingPhotosManager
                        objectId={object.id}
                        photos={photos}
                        onPhotosChange={setPhotos}
                    />

                    {remainingSlots > 0 && (
                        <div className="my-4">
                            <h3 className="font-semibold text-sm mb-2">Додати ще фото</h3>
                            <PhotoUploader
                                photos={newPhotos}
                                onChange={setNewPhotos}
                                maxCount={remainingSlots}
                            />
                        </div>
                    )}

                    {uploading && uploadProgress.total > 0 && (
                        <div className="my-4">
                            <div className="flex justify-between text-xs text-gray-600 mb-1">
                                <span>Завантаження фото…</span>
                                <span>{uploadProgress.done} / {uploadProgress.total}</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                                <div
                                    className="bg-amber-600 h-2 transition-all duration-300"
                                    style={{width: `${(uploadProgress.done / uploadProgress.total) * 100}%`}}
                                />
                            </div>
                        </div>
                    )}
                </ObjectForm>
            </div>
        </div>
    );
}
