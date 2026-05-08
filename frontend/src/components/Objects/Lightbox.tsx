import {useEffect} from 'react';
import {Swiper, SwiperSlide} from 'swiper/react';
import {Navigation, Keyboard} from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/navigation';
import type {ObjectPhoto} from '../../types';

interface Props {
    photos: ObjectPhoto[];
    initialIndex: number;
    onClose: () => void;
}

export default function Lightbox({photos, initialIndex, onClose}: Props) {
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [onClose]);

    return (
        <div className="fixed inset-0 z-50 bg-black/95 flex flex-col">
            <button
                onClick={onClose}
                className="absolute top-4 right-4 z-10 text-white text-3xl w-10 h-10 flex items-center justify-center"
                aria-label="Закрити"
            >✕</button>

            <Swiper
                modules={[Navigation, Keyboard]}
                navigation
                keyboard
                initialSlide={initialIndex}
                className="flex-1 w-full"
            >
                {photos.map((p, i) => (
                    <SwiperSlide key={p.id} className="flex flex-col items-center justify-center">
                        <div className="text-white text-sm mb-2">{i + 1} / {photos.length}</div>
                        <img src={p.image_url} alt={p.caption || ''} className="max-h-[80vh] max-w-full object-contain"/>
                        {p.caption && <p className="text-white mt-3 text-center px-4">{p.caption}</p>}
                        <p className="text-gray-400 text-xs mt-1">
                            Завантажив: {p.uploaded_by.username} · {new Date(p.created_at).toLocaleDateString('uk-UA')}
                        </p>
                    </SwiperSlide>
                ))}
            </Swiper>
        </div>
    );
}
