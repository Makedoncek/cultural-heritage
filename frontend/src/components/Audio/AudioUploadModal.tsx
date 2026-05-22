import {useEffect, useState} from 'react';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {audioService} from '../../services/audio.service';
import type {AudioLanguage, ObjectAudio} from '../../types/audio';
import AudioRecorder from './AudioRecorder';

interface Props {
    objectId: number;
    onClose: () => void;
    onUploaded: (audio: ObjectAudio) => void;
}

const LANGUAGE_VALUES: AudioLanguage[] = ['uk', 'en', 'pl', 'de'];

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_MIMES = new Set([
    'audio/mpeg', 'audio/mp3', 'audio/mp4', 'audio/webm',
    'audio/ogg', 'audio/wav', 'audio/x-m4a', 'audio/x-wav',
]);

export default function AudioUploadModal({objectId, onClose, onUploaded}: Props) {
    const {t} = useTranslation();
    const [mode, setMode] = useState<'upload' | 'record'>('upload');
    const [file, setFile] = useState<File | null>(null);
    const [language, setLanguage] = useState<AudioLanguage>('uk');
    const [title, setTitle] = useState('');
    const [narrator, setNarrator] = useState('');
    const [copyrightOk, setCopyrightOk] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    useEffect(() => {
        if (!file) {
            setPreviewUrl(null);
            return;
        }
        const url = URL.createObjectURL(file);
        setPreviewUrl(url);
        return () => URL.revokeObjectURL(url);
    }, [file]);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        if (f.size > MAX_FILE_SIZE) {
            toast.error(t('audio.modal.fileTooBig'));
            e.target.value = '';
            setFile(null);
            return;
        }
        // Browser may report '' for unknown types — reject anything not whitelisted.
        if (!f.type || !ALLOWED_MIMES.has(f.type)) {
            toast.error(t('audio.modal.unsupportedFormat', {type: f.type || '—'}));
            e.target.value = '';
            setFile(null);
            return;
        }
        setFile(f);
    };

    const handleRecordingComplete = (blob: Blob, _durationSec: number) => {
        const recorded = new File([blob], `recording-${Date.now()}.webm`, {type: blob.type});
        setFile(recorded);
        toast.success(t('audio.modal.recordingDone'));
    };

    const submit = async () => {
        if (!file) return toast.error(t('audio.modal.errSelectFile'));
        if (!title.trim()) return toast.error(t('audio.modal.errTitle'));
        if (!copyrightOk) return toast.error(t('audio.modal.errCopyright'));
        setUploading(true);
        try {
            const created = await audioService.upload(objectId, {
                audio: file,
                language,
                title: title.trim(),
                narrator_name: narrator.trim() || undefined,
                copyright_confirmed: true,
            });
            toast.success(t('audio.modal.uploadSuccess'));
            onUploaded(created);
        } catch (e) {
            const detail = (e as {response?: {data?: {detail?: string; audio?: string[]}}}).response?.data;
            toast.error(detail?.detail || detail?.audio?.[0] || t('audio.modal.uploadError'));
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[9999] bg-black/60 flex items-center justify-center p-4 overflow-y-auto" onClick={onClose}>
            <div
                onClick={(e) => e.stopPropagation()}
                className="bg-white dark:bg-stone-900 rounded-lg w-full max-w-md max-h-[90vh] overflow-y-auto border border-gray-200 dark:border-stone-700"
            >
                <div className="p-4 border-b border-gray-200 dark:border-stone-700 flex justify-between items-center">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-stone-100">
                        🎙 {t('audio.modal.title')}
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
                            {t('audio.modal.tabUpload')}
                        </button>
                        <button
                            type="button"
                            onClick={() => setMode('record')}
                            className={`flex-1 px-3 py-2 text-sm rounded-lg border ${mode === 'record' ? 'bg-amber-100 dark:bg-amber-900/40 border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-300' : 'border-gray-200 dark:border-stone-700 text-gray-600 dark:text-stone-300'} cursor-pointer`}
                        >
                            {t('audio.modal.tabRecord')}
                        </button>
                    </div>

                    {mode === 'upload' ? (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">{t('audio.modal.fileLabel')}</label>
                            <input
                                type="file"
                                accept="audio/*"
                                onChange={handleFileChange}
                                className="block w-full text-sm text-gray-700 dark:text-stone-200 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-amber-600 file:text-white dark:file:bg-amber-500 dark:file:text-stone-900 hover:file:bg-amber-700 dark:hover:file:bg-amber-400 file:cursor-pointer cursor-pointer"
                            />
                            {file && <p className="text-xs text-gray-500 dark:text-stone-400 mt-1">{t('audio.modal.fileSize', {name: file.name, kb: Math.round(file.size / 1024)})}</p>}
                        </div>
                    ) : (
                        <div className="py-4">
                            <AudioRecorder onComplete={handleRecordingComplete} maxDurationSec={180}/>
                            {file && file.name.startsWith('recording-') && (
                                <p className="text-xs text-center text-gray-500 dark:text-stone-400 mt-2">
                                    {t('audio.modal.recordingFile', {kb: Math.round(file.size / 1024)})}
                                </p>
                            )}
                        </div>
                    )}

                    {previewUrl && (
                        <div>
                            <p className="text-xs text-gray-500 dark:text-stone-400 mb-1">{t('audio.modal.preview')}</p>
                            <audio
                                src={previewUrl}
                                controls
                                preload="metadata"
                                className="w-full"
                            />
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">{t('audio.modal.titleLabel')} *</label>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            maxLength={150}
                            className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">{t('audio.modal.languageLabel')} *</label>
                        <select
                            value={language}
                            onChange={(e) => setLanguage(e.target.value as AudioLanguage)}
                            className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 cursor-pointer"
                        >
                            {LANGUAGE_VALUES.map(l => <option key={l} value={l}>{t(`audio.languages.${l}`)}</option>)}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">{t('audio.modal.narratorLabel')}</label>
                        <input
                            type="text"
                            value={narrator}
                            onChange={(e) => setNarrator(e.target.value)}
                            maxLength={100}
                            placeholder={t('audio.modal.narratorPlaceholder')}
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
                            {t('audio.modal.copyrightConfirm')} *
                        </span>
                    </label>

                    <div className="flex justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-3 py-2 text-sm border border-gray-300 dark:border-stone-600 text-gray-700 dark:text-stone-200 rounded-lg hover:bg-gray-100 dark:hover:bg-stone-800 cursor-pointer"
                        >
                            {t('audio.modal.cancel')}
                        </button>
                        <button
                            type="button"
                            onClick={submit}
                            disabled={uploading || !file || !title.trim() || !copyrightOk}
                            className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50"
                        >
                            {uploading ? t('audio.modal.submitting') : t('audio.modal.submit')}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
