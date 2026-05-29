import {useEffect, useRef, useState} from 'react';
import {useTranslation} from 'react-i18next';

interface Props {
    onComplete: (blob: Blob, durationSec: number) => void;
    maxDurationSec?: number;
}

export default function AudioRecorder({onComplete, maxDurationSec = 180}: Readonly<Props>) {
    const {t} = useTranslation();
    const [recording, setRecording] = useState(false);
    const [elapsed, setElapsed] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const recorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const timerRef = useRef<number | null>(null);
    const startedAtRef = useRef<number>(0);

    useEffect(() => () => {
        recorderRef.current?.stream.getTracks().forEach(t => t.stop());
        if (timerRef.current) clearInterval(timerRef.current);
    }, []);

    const start = async () => {
        setError(null);
        chunksRef.current = [];
        try {
            const stream = await navigator.mediaDevices.getUserMedia({audio: true});
            const mime = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
            const rec = mime ? new MediaRecorder(stream, {mimeType: mime}) : new MediaRecorder(stream);
            rec.ondataavailable = (e) => {
                if (e.data.size) chunksRef.current.push(e.data);
            };
            rec.onstop = () => {
                const duration = Math.round((Date.now() - startedAtRef.current) / 1000);
                const blob = new Blob(chunksRef.current, {type: mime || 'audio/webm'});
                stream.getTracks().forEach(t => t.stop());
                onComplete(blob, duration);
            };
            rec.start();
            recorderRef.current = rec;
            startedAtRef.current = Date.now();
            setRecording(true);
            setElapsed(0);
            timerRef.current = globalThis.setInterval(() => {
                const e = Math.round((Date.now() - startedAtRef.current) / 1000);
                setElapsed(e);
                if (e >= maxDurationSec) stop();
            }, 250);
        } catch (e) {
            const name = (e as Error).name;
            if (name === 'NotAllowedError') setError(t('audio.recorder.errPermission'));
            else if (name === 'NotFoundError') setError(t('audio.recorder.errNoMic'));
            else setError(t('audio.recorder.errGeneric'));
        }
    };

    const stop = () => {
        if (recorderRef.current?.state === 'recording') {
            recorderRef.current.stop();
        }
        if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
        }
        setRecording(false);
    };

    const m = Math.floor(elapsed / 60);
    const s = elapsed % 60;

    return (
        <div className="flex flex-col items-center gap-2">
            {!recording ? (
                <button
                    type="button"
                    onClick={start}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center gap-2 cursor-pointer"
                >
                    {t('audio.recorder.start')}
                </button>
            ) : (
                <>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-red-600 animate-pulse"/>
                        <span className="font-mono text-lg text-gray-900 dark:text-stone-100">
                            {m}:{s.toString().padStart(2, '0')} / {Math.floor(maxDurationSec / 60)}:{(maxDurationSec % 60).toString().padStart(2, '0')}
                        </span>
                    </div>
                    <button
                        type="button"
                        onClick={stop}
                        className="px-4 py-2 bg-gray-700 hover:bg-gray-800 text-white rounded-lg cursor-pointer"
                    >
                        {t('audio.recorder.stop')}
                    </button>
                </>
            )}
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        </div>
    );
}
