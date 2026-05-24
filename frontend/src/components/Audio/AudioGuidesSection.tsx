import {useEffect, useState} from 'react';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {audioService} from '../../services/audio.service';
import type {AudioLanguage, ObjectAudio} from '../../types/audio';
import AudioPlayer from './AudioPlayer';
import AudioUploadModal from './AudioUploadModal';
import AudioEditModal from './AudioEditModal';
import ReportInaccuracyButton from '../Objects/ReportInaccuracyButton';
import {useAuth} from '../../context/AuthContext';

interface Props {
    objectId: number;
    objectTitle?: string;
    coverUrl?: string | null;
}

const LANG_TO_ISO: Record<AudioLanguage, string> = {
    uk: 'ua',
    en: 'gb',
    pl: 'pl',
    de: 'de',
};

const LANG_LABEL: Record<AudioLanguage, string> = {
    uk: 'UA',
    en: 'EN',
    pl: 'PL',
    de: 'DE',
};

export default function AudioGuidesSection({objectId, objectTitle, coverUrl}: Props) {
    const {t} = useTranslation();
    const {isAuthenticated, user} = useAuth();
    const [audios, setAudios] = useState<ObjectAudio[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<AudioLanguage | 'all'>('all');
    const [showUpload, setShowUpload] = useState(false);
    const [editingAudio, setEditingAudio] = useState<ObjectAudio | null>(null);

    useEffect(() => {
        setLoading(true);
        audioService.list(objectId)
            .then(setAudios)
            .catch(() => toast.error(t('audio.loadError')))
            .finally(() => setLoading(false));
    }, [objectId, t]);

    const visible = filter === 'all' ? audios : audios.filter(a => a.language === filter);
    const availableLanguages = Array.from(new Set(audios.map(a => a.language)));

    const handleUploaded = (a: ObjectAudio) => {
        setAudios(prev => [a, ...prev]);
        setShowUpload(false);
    };

    const handleDelete = async (audio: ObjectAudio) => {
        if (!confirm(t('audio.deleteConfirm'))) return;
        try {
            await audioService.remove(objectId, audio.id);
            setAudios(prev => prev.filter(a => a.id !== audio.id));
            toast.success(t('audio.deleteSuccess'));
        } catch {
            toast.error(t('audio.deleteError'));
        }
    };

    return (
        <div className="my-6">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-stone-100">
                    🎧 {t('audio.sectionTitle')} {audios.length > 0 && <span className="text-sm text-gray-500 dark:text-stone-400 font-normal">({audios.length})</span>}
                </h3>
                {isAuthenticated && (
                    <button
                        type="button"
                        onClick={() => setShowUpload(true)}
                        className="px-3 py-1.5 text-sm bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer"
                    >
                        {t('audio.addBtn')}
                    </button>
                )}
            </div>

            {audios.length > 1 && availableLanguages.length > 1 && (
                <div className="flex gap-2 mb-3 flex-wrap">
                    {(['all', ...availableLanguages] as const).map(l => (
                        <button
                            key={l}
                            type="button"
                            onClick={() => setFilter(l as AudioLanguage | 'all')}
                            className={`inline-flex items-center gap-2 px-3.5 py-1.5 text-sm font-medium rounded-full border cursor-pointer transition-colors ${
                                filter === l
                                    ? 'bg-amber-100 dark:bg-amber-900/40 border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-300'
                                    : 'border-gray-200 dark:border-stone-700 text-gray-600 dark:text-stone-300 hover:border-gray-400'
                            }`}
                        >
                            {l === 'all' ? (
                                t('audio.filterAll')
                            ) : (
                                <>
                                    <img
                                        src={`https://flagcdn.com/20x15/${LANG_TO_ISO[l as AudioLanguage]}.png`}
                                        alt=""
                                        width={20}
                                        height={15}
                                        className="rounded-[2px]"
                                    />
                                    {LANG_LABEL[l as AudioLanguage]}
                                </>
                            )}
                        </button>
                    ))}
                </div>
            )}

            {loading ? (
                <p className="text-sm text-gray-500 dark:text-stone-400">{t('audio.loading')}</p>
            ) : visible.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-stone-400">
                    {audios.length === 0 ? t('audio.empty') : t('audio.emptyForLang')}
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
                                            {t(`audio.status.${a.status}`)}
                                        </span>
                                        {a.moderation_note && (
                                            <span className="ml-2 text-xs text-gray-500 dark:text-stone-400">
                                                {a.moderation_note}
                                            </span>
                                        )}
                                    </div>
                                )}
                                <AudioPlayer audio={a} objectTitle={objectTitle} coverUrl={coverUrl}/>
                                <div className="flex items-center justify-between gap-3 mt-2 flex-wrap">
                                    <p className="text-xs text-gray-500 dark:text-stone-400">
                                        @{a.uploaded_by.username} · {a.language_label}
                                    </p>
                                    {canDelete ? (
                                        <div className="flex gap-2">
                                            <button
                                                type="button"
                                                onClick={() => setEditingAudio(a)}
                                                className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400 text-white rounded-lg cursor-pointer"
                                            >
                                                ✏️ {t('audio.editLink')}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => handleDelete(a)}
                                                className="px-3 py-1.5 text-sm bg-red-500 hover:bg-red-600 text-white rounded-lg cursor-pointer"
                                            >
                                                🗑 {t('audio.deleteLink')}
                                            </button>
                                        </div>
                                    ) : (
                                        <ReportInaccuracyButton targetType="audio" targetId={a.id} targetTitle={a.title} compact/>
                                    )}
                                </div>
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

            {editingAudio && (
                <AudioEditModal
                    audio={editingAudio}
                    onClose={() => setEditingAudio(null)}
                    onSaved={(updated) => {
                        setAudios(prev => prev.map(a => a.id === updated.id ? updated : a));
                        setEditingAudio(null);
                    }}
                />
            )}
        </div>
    );
}
