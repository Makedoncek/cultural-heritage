import {useState} from 'react';
import toast from 'react-hot-toast';
import {audioService} from '../../services/audio.service';
import type {AudioLanguage, ObjectAudio} from '../../types/audio';
import AudioRecorder from './AudioRecorder';

interface Props {
    objectId: number;
    onClose: () => void;
    onUploaded: (audio: ObjectAudio) => void;
}

const LANGUAGES: {value: AudioLanguage; label: string}[] = [
    {value: 'uk', label: '🇺🇦 Українська'},
    {value: 'en', label: '🇬🇧 English'},
    {value: 'pl', label: '🇵🇱 Polski'},
    {value: 'de', label: '🇩🇪 Deutsch'},
];

const MAX_FILE_SIZE = 10 * 1024 * 1024;

export default function AudioUploadModal({objectId, onClose, onUploaded}: Props) {
    const [mode, setMode] = useState<'upload' | 'record'>('upload');
    const [file, setFile] = useState<File | null>(null);
    const [language, setLanguage] = useState<AudioLanguage>('uk');
    const [title, setTitle] = useState('');
    const [narrator, setNarrator] = useState('');
    const [copyrightOk, setCopyrightOk] = useState(false);
    const [uploading, setUploading] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        if (f.size > MAX_FILE_SIZE) {
            toast.error('Файл більший за 10 МБ');
            return;
        }
        setFile(f);
    };

    const handleRecordingComplete = (blob: Blob, _durationSec: number) => {
        const recorded = new File([blob], `recording-${Date.now()}.webm`, {type: blob.type});
        setFile(recorded);
        toast.success('Запис завершено');
    };

    const submit = async () => {
        if (!file) return toast.error('Оберіть або запишіть файл');
        if (!title.trim()) return toast.error('Введіть назву');
        if (!copyrightOk) return toast.error('Підтвердьте право на публікацію');
        setUploading(true);
        try {
            const created = await audioService.upload(objectId, {
                audio: file,
                language,
                title: title.trim(),
                narrator_name: narrator.trim() || undefined,
                copyright_confirmed: true,
            });
            toast.success('Завантажено. Очікує модерації.');
            onUploaded(created);
        } catch (e) {
            const detail = (e as {response?: {data?: {detail?: string; audio?: string[]}}}).response?.data;
            toast.error(detail?.detail || detail?.audio?.[0] || 'Не вдалося завантажити');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
            <div
                onClick={(e) => e.stopPropagation()}
                className="bg-white dark:bg-stone-900 rounded-lg w-full max-w-md max-h-[90vh] overflow-y-auto border border-gray-200 dark:border-stone-700"
            >
                <div className="p-4 border-b border-gray-200 dark:border-stone-700 flex justify-between items-center">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-stone-100">
                        🎙 Додати аудіо-нарратив
                    </h3>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700 dark:text-stone-400 dark:hover:text-stone-200 text-xl cursor-pointer">✕</button>
                </div>
                <div className="p-4 space-y-4">
                    <div className="flex gap-2">
                        <button
                            type="button"
                            onClick={() => setMode('upload')}
                            className={`flex-1 px-3 py-2 text-sm rounded-lg border ${mode === 'upload' ? 'bg-amber-100 dark:bg-amber-900/40 border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-300' : 'border-gray-200 dark:border-stone-700 text-gray-600 dark:text-stone-300'} cursor-pointer`}
                        >
                            📁 Завантажити
                        </button>
                        <button
                            type="button"
                            onClick={() => setMode('record')}
                            className={`flex-1 px-3 py-2 text-sm rounded-lg border ${mode === 'record' ? 'bg-amber-100 dark:bg-amber-900/40 border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-300' : 'border-gray-200 dark:border-stone-700 text-gray-600 dark:text-stone-300'} cursor-pointer`}
                        >
                            🎙 Записати
                        </button>
                    </div>

                    {mode === 'upload' ? (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">Файл (mp3, m4a, webm, ogg, wav, до 10 МБ)</label>
                            <input
                                type="file"
                                accept="audio/*"
                                onChange={handleFileChange}
                                className="w-full text-sm text-gray-700 dark:text-stone-200"
                            />
                            {file && <p className="text-xs text-gray-500 dark:text-stone-400 mt-1">{file.name} ({Math.round(file.size / 1024)} КБ)</p>}
                        </div>
                    ) : (
                        <div className="py-4">
                            <AudioRecorder onComplete={handleRecordingComplete} maxDurationSec={180}/>
                            {file && file.name.startsWith('recording-') && (
                                <p className="text-xs text-center text-gray-500 dark:text-stone-400 mt-2">
                                    ✓ Запис: {Math.round(file.size / 1024)} КБ
                                </p>
                            )}
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">Назва *</label>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            maxLength={150}
                            className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">Мова *</label>
                        <select
                            value={language}
                            onChange={(e) => setLanguage(e.target.value as AudioLanguage)}
                            className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 cursor-pointer"
                        >
                            {LANGUAGES.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">Диктор (опціонально)</label>
                        <input
                            type="text"
                            value={narrator}
                            onChange={(e) => setNarrator(e.target.value)}
                            maxLength={100}
                            placeholder="Ім'я диктора"
                            className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                        />
                    </div>

                    <label className="flex items-start gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={copyrightOk}
                            onChange={(e) => setCopyrightOk(e.target.checked)}
                            className="mt-0.5 w-4 h-4 accent-amber-500 cursor-pointer"
                        />
                        <span className="text-xs text-gray-700 dark:text-stone-200">
                            Підтверджую, що я є автором цього аудіо або маю право на його публікацію *
                        </span>
                    </label>

                    <div className="flex justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-3 py-2 text-sm border border-gray-300 dark:border-stone-600 text-gray-700 dark:text-stone-200 rounded-lg hover:bg-gray-100 dark:hover:bg-stone-800 cursor-pointer"
                        >
                            Скасувати
                        </button>
                        <button
                            type="button"
                            onClick={submit}
                            disabled={uploading || !file || !title.trim() || !copyrightOk}
                            className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50"
                        >
                            {uploading ? 'Завантаження...' : 'Завантажити'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
