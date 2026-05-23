import {useState} from 'react';
import {Link} from 'react-router';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {audioService} from '../../services/audio.service';
import {usePaginatedList} from '../../hooks/usePaginatedList';
import LoadMoreButton from '../common/LoadMoreButton';
import AudioPlayer from '../Audio/AudioPlayer';
import AudioEditModal from '../Audio/AudioEditModal';
import type {ObjectAudio, ObjectWithMyAudios} from '../../types/audio';

function countByStatus(audios: ObjectAudio[]) {
    const c = {approved: 0, pending: 0, rejected: 0};
    audios.forEach(a => { c[a.status]++; });
    return c;
}

export default function MyAudiosTab() {
    const {t} = useTranslation();
    const {items, setItems, count: totalCount, nextUrl, loading, loadingMore, loadMore, error} = usePaginatedList<ObjectWithMyAudios>({
        initialFetch: () => audioService.listMine(),
        fetchByUrl: (url) => audioService.listMineByUrl(url),
        onError: () => toast.error(t('common.loadMoreError')),
        deps: [],
    });
    const [editingAudio, setEditingAudio] = useState<ObjectAudio | null>(null);

    const handleAudioUpdated = (objectId: number, updated: ObjectAudio) => {
        setItems(prev => prev.map(obj =>
            obj.id !== objectId ? obj : {...obj, my_audios: obj.my_audios.map(a => a.id === updated.id ? updated : a)},
        ));
    };

    const handleDelete = async (objectId: number, audio: ObjectAudio) => {
        if (!confirm(t('audio.deleteConfirm'))) return;
        try {
            await audioService.remove(objectId, audio.id);
            setItems(prev => prev
                .map(obj => obj.id !== objectId ? obj : {...obj, my_audios: obj.my_audios.filter(a => a.id !== audio.id)})
                .filter(obj => obj.my_audios.length > 0)
            );
            toast.success(t('audio.deleteSuccess'));
        } catch {
            toast.error(t('audio.deleteError'));
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
            </div>
        );
    }
    if (error && items.length === 0) {
        return <p className="text-red-600 text-center py-6">{t('audio.loadError')}</p>;
    }
    if (items.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500 dark:text-stone-400 mb-4">{t('contributions.audiosEmpty')}</p>
                <Link to="/" className="text-amber-600 dark:text-amber-400 hover:underline">
                    {t('myPhotos.goToMap')}
                </Link>
            </div>
        );
    }

    return (
        <>
            <div className="space-y-4">
                {items.map(obj => {
                    const counts = countByStatus(obj.my_audios);
                    return (
                        <div
                            key={obj.id}
                            className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-3 hover:border-amber-300 dark:hover:border-amber-500 transition-colors"
                        >
                            <div className="mb-2">
                                <Link
                                    to={`/objects/${obj.id}`}
                                    className="text-lg font-semibold text-gray-900 dark:text-stone-100 hover:text-amber-700 dark:hover:text-amber-400"
                                >
                                    {obj.title}
                                </Link>
                                <p className="text-sm text-gray-600 dark:text-stone-300 mt-1">
                                    {t('myPhotos.authorByLine', {name: obj.author_name})}
                                </p>
                                {obj.tags.length > 0 && (
                                    <div className="flex flex-wrap gap-1.5 mt-2">
                                        {obj.tags.map(tg => (
                                            <span
                                                key={tg.id}
                                                className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded-full text-xs"
                                            >
                                                {tg.icon} {tg.name}
                                            </span>
                                        ))}
                                    </div>
                                )}
                                <div className="flex flex-wrap gap-2 mt-2 text-xs">
                                    <span className="text-gray-700 dark:text-stone-200">
                                        {t('contributions.myAudiosCount')} <strong>{obj.my_audios.length}</strong>
                                    </span>
                                    {counts.approved > 0 && (
                                        <span className="text-green-700 dark:text-green-400">✓ {t('myPhotos.approvedCount', {count: counts.approved})}</span>
                                    )}
                                    {counts.pending > 0 && (
                                        <span className="text-yellow-700 dark:text-yellow-400">⏳ {t('myPhotos.pendingCount', {count: counts.pending})}</span>
                                    )}
                                    {counts.rejected > 0 && (
                                        <span className="text-red-700">✕ {t('myPhotos.rejectedCount', {count: counts.rejected})}</span>
                                    )}
                                </div>
                            </div>

                            <div className="space-y-2 mt-3">
                                {obj.my_audios.map(a => (
                                    <div key={a.id}>
                                        {a.status !== 'approved' && (
                                            <div className="mb-1">
                                                <span className={`px-2 py-0.5 text-xs rounded ${a.status === 'pending' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300' : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'}`}>
                                                    {t(`audio.status.${a.status}`)}
                                                </span>
                                                {a.moderation_note && (
                                                    <span className="ml-2 text-xs text-gray-500 dark:text-stone-400">{a.moderation_note}</span>
                                                )}
                                            </div>
                                        )}
                                        <AudioPlayer audio={a} objectTitle={obj.title}/>
                                        <div className="flex gap-2 mt-2">
                                            <button
                                                type="button"
                                                onClick={() => setEditingAudio(a)}
                                                className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400 text-white rounded-lg cursor-pointer"
                                            >
                                                ✏️ {t('audio.editLink')}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => handleDelete(obj.id, a)}
                                                className="px-3 py-1.5 text-sm bg-red-500 hover:bg-red-600 text-white rounded-lg cursor-pointer"
                                            >
                                                🗑 {t('audio.deleteLink')}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
                <LoadMoreButton
                    show={!!nextUrl}
                    loading={loadingMore}
                    shown={items.length}
                    total={totalCount}
                    onClick={loadMore}
                />
            </div>
            {editingAudio && (
                <AudioEditModal
                    audio={editingAudio}
                    onClose={() => setEditingAudio(null)}
                    onSaved={(updated) => {
                        handleAudioUpdated(updated.cultural_object, updated);
                        setEditingAudio(null);
                    }}
                />
            )}
        </>
    );
}
