import {useEffect, useRef, useState} from 'react';
import {audioService} from '../../services/audio.service';
import type {ObjectAudio} from '../../types/audio';

interface Props {
    audio: ObjectAudio;
    objectTitle?: string;
    coverUrl?: string | null;
}

function fmt(s: number): string {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({audio, objectTitle, coverUrl}: Props) {
    const audioRef = useRef<HTMLAudioElement>(null);
    const [playing, setPlaying] = useState(false);
    const [progress, setProgress] = useState(0);
    const [duration, setDuration] = useState(audio.duration_seconds);
    const incrementedRef = useRef(false);

    useEffect(() => {
        if ('mediaSession' in navigator) {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: audio.title,
                artist: audio.narrator_name || 'CultureMap',
                album: objectTitle || '',
                artwork: coverUrl ? [{src: coverUrl, sizes: '512x512'}] : [],
            });
            navigator.mediaSession.setActionHandler('play', () => audioRef.current?.play());
            navigator.mediaSession.setActionHandler('pause', () => audioRef.current?.pause());
            navigator.mediaSession.setActionHandler('seekbackward', () => {
                if (audioRef.current) audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 15);
            });
            navigator.mediaSession.setActionHandler('seekforward', () => {
                if (audioRef.current) audioRef.current.currentTime += 15;
            });
        }
    }, [audio, objectTitle, coverUrl]);

    const togglePlay = () => {
        const el = audioRef.current;
        if (!el) return;
        if (el.paused) {
            el.play();
            if (!incrementedRef.current) {
                incrementedRef.current = true;
                audioService.incrementPlayCount(audio.cultural_object, audio.id).catch(() => {});
            }
        } else {
            el.pause();
        }
    };

    const onSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (audioRef.current) audioRef.current.currentTime = Number(e.target.value);
    };

    return (
        <div className="bg-white dark:bg-stone-900 border border-gray-200 dark:border-stone-700 rounded-lg p-3 flex items-center gap-3">
            <audio
                ref={audioRef}
                src={audio.cloudinary_url}
                preload="metadata"
                onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || audio.duration_seconds)}
                onPlay={() => setPlaying(true)}
                onPause={() => setPlaying(false)}
                onTimeUpdate={(e) => setProgress(e.currentTarget.currentTime)}
                onEnded={() => setPlaying(false)}
            />
            <button
                type="button"
                onClick={togglePlay}
                className="shrink-0 w-12 h-12 rounded-full bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 text-xl flex items-center justify-center cursor-pointer"
                aria-label={playing ? 'Pause' : 'Play'}
            >
                {playing ? '⏸' : '▶'}
            </button>
            <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-2">
                    <p className="text-sm font-medium text-gray-900 dark:text-stone-100 truncate">
                        {audio.title}
                    </p>
                    <span className="text-xs text-gray-500 dark:text-stone-400 shrink-0">
                        {fmt(progress)} / {fmt(duration)}
                    </span>
                </div>
                {audio.narrator_name && (
                    <p className="text-xs text-gray-500 dark:text-stone-400 truncate">
                        🎙 {audio.narrator_name}
                    </p>
                )}
                <input
                    type="range"
                    min={0}
                    max={duration || 0}
                    value={progress}
                    step={0.1}
                    onChange={onSeek}
                    className="w-full mt-1 accent-amber-500 cursor-pointer"
                />
                <p className="text-[10px] text-gray-400 dark:text-stone-500">
                    ▶ {audio.plays_count}
                </p>
            </div>
        </div>
    );
}
