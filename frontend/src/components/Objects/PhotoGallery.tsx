import {useState} from 'react';
import {useTranslation} from 'react-i18next';
import type {ObjectPhoto} from '../../types';
import Lightbox from './Lightbox';

interface Props {
    photos: ObjectPhoto[];
}

export default function PhotoGallery({photos}: Props) {
    const {t} = useTranslation();
    const [lightboxIdx, setLightboxIdx] = useState<number | null>(null);

    if (photos.length === 0) return null;

    const cover = photos[0];

    return (
        <div>
            <button
                type="button"
                onClick={() => setLightboxIdx(0)}
                className="block cursor-pointer w-full aspect-video bg-gray-100 dark:bg-stone-800 rounded overflow-hidden"
            >
                <img src={cover.image_url} alt={cover.caption || ''} className="w-full h-full object-cover"/>
            </button>

            {photos.length > 1 && (
                <div className="flex gap-2 mt-3 overflow-x-auto pb-2">
                    {photos.map((p, i) => (
                        <button
                            key={p.id}
                            type="button"
                            onClick={() => setLightboxIdx(i)}
                            className={`relative w-24 h-20 flex-shrink-0 cursor-pointer rounded overflow-hidden border-2 ${
                                i === 0 ? 'border-blue-500' : 'border-transparent'
                            }`}
                        >
                            <img src={p.thumbnail_url} alt="" className="w-full h-full object-cover"/>
                            {p.status === 'pending' && (
                                <span className="absolute bottom-0 left-0 right-0 bg-yellow-500 text-white text-[10px] text-center">
                                    {t('photo.underReview')}
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            )}

            {lightboxIdx !== null && (
                <Lightbox photos={photos} initialIndex={lightboxIdx} onClose={() => setLightboxIdx(null)}/>
            )}
        </div>
    );
}
