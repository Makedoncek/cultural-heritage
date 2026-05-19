import {useEffect} from 'react';
import {Swiper, SwiperSlide} from 'swiper/react';
import {Navigation, Keyboard} from 'swiper/modules';
import {useTranslation} from 'react-i18next';
import 'swiper/css';
import 'swiper/css/navigation';
import type {ObjectPhoto} from '../../types';

interface Props {
    photos: ObjectPhoto[];
    initialIndex: number;
    onClose: () => void;
}

export default function Lightbox({photos, initialIndex, onClose}: Props) {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [onClose]);

    return (
        <div className="fixed inset-0 z-[9999] bg-black/95 flex flex-col">
            <button
                onClick={onClose}
                className="absolute top-4 right-4 z-10 text-white text-3xl w-10 h-10 flex items-center justify-center cursor-pointer"
                aria-label="Close"
            >✕</button>

            <Swiper
                modules={[Navigation, Keyboard]}
                navigation
                keyboard
                initialSlide={initialIndex}
                className="flex-1 w-full"
            >
                {photos.map((p, i) => (
                    <SwiperSlide key={p.id}>
                        <div className="w-full h-full flex flex-col items-center justify-center px-12">
                            <div className="text-white text-sm mb-2">{i + 1} / {photos.length}</div>
                            <img
                                src={p.image_url}
                                alt={p.caption || ''}
                                className="max-h-[75vh] max-w-[85vw] object-contain"
                            />
                            {p.caption && (
                                <p className="text-white mt-3 text-center px-4 max-w-[85vw]">{p.caption}</p>
                            )}
                            <p className="text-gray-400 text-xs mt-1">
                                {t('photo.byUploaderDate', {
                                    user: p.uploaded_by.username,
                                    date: new Date(p.created_at).toLocaleDateString(dateLocale),
                                })}
                            </p>
                        </div>
                    </SwiperSlide>
                ))}
            </Swiper>
        </div>
    );
}
