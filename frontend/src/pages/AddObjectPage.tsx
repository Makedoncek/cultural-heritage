import {useState} from 'react';
import {useNavigate} from 'react-router';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {objectsService} from '../services/objects.service';
import {photosService, extractUploadError} from '../services/photos.service';
import ObjectForm from '../components/Objects/ObjectForm';
import PhotoUploader, {type PendingPhoto} from '../components/Objects/PhotoUploader';
import DuplicateWarningModal from '../components/Objects/DuplicateWarningModal';
import type {CulturalObjectWrite} from '../types';

const MAX_AUTHOR_PHOTOS = 5;

interface NearbyObject {
    id: number;
    title: string;
    distance_m: number;
}

export default function AddObjectPage() {
    const navigate = useNavigate();
    const {t} = useTranslation();
    const [photos, setPhotos] = useState<PendingPhoto[]>([]);
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState({done: 0, total: 0});
    const [duplicateCheck, setDuplicateCheck] = useState<{nearby: NearbyObject[]; pendingData: CulturalObjectWrite} | null>(null);

    const doSubmit = async (data: CulturalObjectWrite) => {
        const obj = await objectsService.create(data);

        if (photos.length === 0) {
            toast.success(t('object.sentForModeration'));
            navigate('/my-objects');
            return;
        }

        setUploading(true);
        setProgress({done: 0, total: photos.length});
        const failures: {name: string; reason: string}[] = [];
        for (const p of photos) {
            try {
                await photosService.upload(obj.id, p.file, p.caption);
                setProgress(prev => ({...prev, done: prev.done + 1}));
            } catch (e) {
                failures.push({name: p.file.name, reason: extractUploadError(e)});
            }
        }
        setUploading(false);

        if (failures.length === 0) {
            toast.success(t('object.createdWithPhotos'));
            navigate('/my-objects');
        } else {
            const message = failures.map(f => `«${f.name}»: ${f.reason}`).join('\n');
            toast.error(message, {duration: 6000});
            navigate(`/objects/${obj.id}`);
        }
    };

    const handleSubmit = async (data: CulturalObjectWrite) => {
        try {
            const {nearby} = await objectsService.checkDuplicates(data.latitude, data.longitude);
            if (nearby.length > 0) {
                setDuplicateCheck({nearby, pendingData: data});
                return;
            }
        } catch {
            // Duplicate-check failure should never block creation — fall through.
        }
        await doSubmit(data);
    };

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100 mb-6">{t('auth.addObjectTitle')}</h1>
                <ObjectForm onSubmit={handleSubmit} submitLabel={t('form.addSubmit')} submittingLabel={t('form.addSubmitting')}>
                    <div className="my-4">
                        <PhotoUploader
                            photos={photos}
                            onChange={setPhotos}
                            maxCount={MAX_AUTHOR_PHOTOS}
                            label={t('photo.addPhotos')}
                        />
                    </div>
                </ObjectForm>
                {uploading && (
                    <div className="mt-3 text-sm text-gray-700 dark:text-stone-200">
                        {t('photo.uploadProgress', {done: progress.done, total: progress.total})}
                    </div>
                )}
            </div>

            {duplicateCheck && (
                <DuplicateWarningModal
                    nearby={duplicateCheck.nearby}
                    onCancel={() => setDuplicateCheck(null)}
                    onProceed={() => {
                        const data = duplicateCheck.pendingData;
                        setDuplicateCheck(null);
                        void doSubmit(data);
                    }}
                    keyPrefix="object.duplicateWarning"
                />
            )}
        </div>
    );
}
