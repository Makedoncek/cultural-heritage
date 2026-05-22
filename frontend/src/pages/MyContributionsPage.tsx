import {useEffect, useState} from 'react';
import {useTranslation} from 'react-i18next';
import MyPhotosTab from '../components/Contributions/MyPhotosTab';
import MyAudiosTab from '../components/Contributions/MyAudiosTab';
import {objectsService} from '../services/objects.service';
import {audioService} from '../services/audio.service';

type Tab = 'photos' | 'audios';

export default function MyContributionsPage() {
    const {t} = useTranslation();
    const [tab, setTab] = useState<Tab>('photos');
    const [photoCount, setPhotoCount] = useState<number | null>(null);
    const [audioCount, setAudioCount] = useState<number | null>(null);

    useEffect(() => {
        objectsService.getWithMyPhotos()
            .then(data => setPhotoCount(data.results.reduce((acc, o) => acc + o.my_photos.length, 0)))
            .catch(() => setPhotoCount(0));
        audioService.listMine()
            .then(data => setAudioCount(data.reduce((acc, o) => acc + o.my_audios.length, 0)))
            .catch(() => setAudioCount(0));
    }, []);

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100 mb-2">
                    {t('contributions.title')}
                </h1>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-6">
                    {t('contributions.subtitle')}
                </p>

                <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-stone-700">
                    <button
                        type="button"
                        onClick={() => setTab('photos')}
                        className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors cursor-pointer ${
                            tab === 'photos'
                                ? 'border-amber-500 text-amber-700 dark:text-amber-400'
                                : 'border-transparent text-gray-500 dark:text-stone-400 hover:text-gray-700 dark:hover:text-stone-200'
                        }`}
                    >
                        📷 {t('contributions.tabPhotos')}
                        {photoCount !== null && (
                            <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${tab === 'photos' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300' : 'bg-gray-100 dark:bg-stone-800 text-gray-600 dark:text-stone-400'}`}>
                                {photoCount}
                            </span>
                        )}
                    </button>
                    <button
                        type="button"
                        onClick={() => setTab('audios')}
                        className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors cursor-pointer ${
                            tab === 'audios'
                                ? 'border-amber-500 text-amber-700 dark:text-amber-400'
                                : 'border-transparent text-gray-500 dark:text-stone-400 hover:text-gray-700 dark:hover:text-stone-200'
                        }`}
                    >
                        🎙 {t('contributions.tabAudios')}
                        {audioCount !== null && (
                            <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${tab === 'audios' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300' : 'bg-gray-100 dark:bg-stone-800 text-gray-600 dark:text-stone-400'}`}>
                                {audioCount}
                            </span>
                        )}
                    </button>
                </div>

                {tab === 'photos' ? <MyPhotosTab/> : <MyAudiosTab/>}
            </div>
        </div>
    );
}
