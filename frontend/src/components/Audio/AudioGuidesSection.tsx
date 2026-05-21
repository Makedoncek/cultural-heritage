import {useEffect, useState} from 'react';
import toast from 'react-hot-toast';
import {audioService} from '../../services/audio.service';
import type {AudioLanguage, ObjectAudio} from '../../types/audio';
import AudioPlayer from './AudioPlayer';
import AudioUploadModal from './AudioUploadModal';
import {useAuth} from '../../context/AuthContext';

interface Props {
    objectId: number;
    objectTitle?: string;
    coverUrl?: string | null;
}

const LANG_LABELS: Record<AudioLanguage | 'all', string> = {
    all: 'Усі',
    uk: '🇺🇦 UA',
    en: '🇬🇧 EN',
    pl: '🇵🇱 PL',
    de: '🇩🇪 DE',
};

export default function AudioGuidesSection({objectId, objectTitle, coverUrl}: Props) {
    const {isAuthenticated, user} = useAuth();
    const [audios, setAudios] = useState<ObjectAudio[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<AudioLanguage | 'all'>('all');
    const [showUpload, setShowUpload] = useState(false);

    useEffect(() => {
        setLoading(true);
        audioService.list(objectId)
            .then(setAudios)
            .catch(() => toast.error('Не вдалося завантажити аудіо'))
            .finally(() => setLoading(false));
    }, [objectId]);

    const visible = filter === 'all' ? audios : audios.filter(a => a.language === filter);
    const availableLanguages = Array.from(new Set(audios.map(a => a.language)));

    const handleUploaded = (a: ObjectAudio) => {
        setAudios(prev => [a, ...prev]);
        setShowUpload(false);
    };

    const handleDelete = async (audio: ObjectAudio) => {
        if (!confirm('Видалити це аудіо?')) return;
        try {
            await audioService.remove(objectId, audio.id);
            setAudios(prev => prev.filter(a => a.id !== audio.id));
            toast.success('Видалено');
        } catch {
            toast.error('Не вдалося видалити');
        }
    };

    return (
        <div className="my-6">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-stone-100">
                    🎧 Аудіо-наративи {audios.length > 0 && <span className="text-sm text-gray-500 dark:text-stone-400 font-normal">({audios.length})</span>}
                </h3>
                {isAuthenticated && (
                    <button
                        type="button"
                        onClick={() => setShowUpload(true)}
                        className="px-3 py-1.5 text-sm bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer"
                    >
                        + Додати
                    </button>
                )}
            </div>

            {audios.length > 1 && availableLanguages.length > 1 && (
                <div className="flex gap-1.5 mb-3 flex-wrap">
                    {(['all', ...availableLanguages] as const).map(l => (
                        <button
                            key={l}
                            type="button"
                            onClick={() => setFilter(l as AudioLanguage | 'all')}
                            className={`px-2.5 py-1 text-xs rounded-full border cursor-pointer ${
                                filter === l
                                    ? 'bg-amber-100 dark:bg-amber-900/40 border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-300'
                                    : 'border-gray-200 dark:border-stone-700 text-gray-600 dark:text-stone-300 hover:border-gray-400'
                            }`}
                        >
                            {LANG_LABELS[l]}
                        </button>
                    ))}
                </div>
            )}

            {loading ? (
                <p className="text-sm text-gray-500 dark:text-stone-400">Завантаження...</p>
            ) : visible.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-stone-400">
                    {audios.length === 0 ? 'Поки що немає аудіо-наративів. Будь першим хто додасть!' : 'Немає аудіо цією мовою.'}
                </p>
            ) : (
                <div className="space-y-2">
                    {visible.map(a => {
                        const canDelete = user && (user.username === a.uploaded_by.username || user.is_staff);
                        return (
                            <div key={a.id} className="relative">
                                {a.status !== 'approved' && (
                                    <div className="mb-1">
                                        <span className={`px-2 py-0.5 text-xs rounded ${a.status === 'pending' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300' : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'}`}>
                                            {a.status_label}
                                        </span>
                                        {a.moderation_note && (
                                            <span className="ml-2 text-xs text-gray-500 dark:text-stone-400">
                                                {a.moderation_note}
                                            </span>
                                        )}
                                    </div>
                                )}
                                <AudioPlayer audio={a} objectTitle={objectTitle} coverUrl={coverUrl}/>
                                <p className="text-[10px] text-gray-400 dark:text-stone-500 mt-1">
                                    @{a.uploaded_by.username} · {a.language_label}
                                    {canDelete && (
                                        <button
                                            type="button"
                                            onClick={() => handleDelete(a)}
                                            className="ml-2 text-red-500 hover:underline cursor-pointer"
                                        >
                                            видалити
                                        </button>
                                    )}
                                </p>
                            </div>
                        );
                    })}
                </div>
            )}

            {showUpload && (
                <AudioUploadModal
                    objectId={objectId}
                    onClose={() => setShowUpload(false)}
                    onUploaded={handleUploaded}
                />
            )}
        </div>
    );
}
