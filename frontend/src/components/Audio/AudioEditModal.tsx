import {useState} from 'react';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {audioService} from '../../services/audio.service';
import type {AudioLanguage, ObjectAudio} from '../../types/audio';

interface Props {
    audio: ObjectAudio;
    onClose: () => void;
    onSaved: (updated: ObjectAudio) => void;
}

const LANGUAGE_VALUES: AudioLanguage[] = ['uk', 'en', 'pl', 'de'];

export default function AudioEditModal({audio, onClose, onSaved}: Props) {
    const {t} = useTranslation();
    const [title, setTitle] = useState(audio.title);
    const [language, setLanguage] = useState<AudioLanguage>(audio.language);
    const [narrator, setNarrator] = useState(audio.narrator_name);
    const [saving, setSaving] = useState(false);

    const dirty =
        title.trim() !== audio.title ||
        language !== audio.language ||
        narrator.trim() !== audio.narrator_name;

    const submit = async () => {
        if (!title.trim()) return toast.error(t('audio.modal.errTitle'));
        if (!dirty) return onClose();
        setSaving(true);
        try {
            const updated = await audioService.update(audio.cultural_object, audio.id, {
                title: title.trim(),
                language,
                narrator_name: narrator.trim(),
            });
            toast.success(t('audio.edit.savedRePending'));
            onSaved(updated);
        } catch (e) {
            const detail = (e as {response?: {data?: {detail?: string}}}).response?.data?.detail;
            toast.error(detail || t('audio.edit.saveError'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[9999] bg-black/60 flex items-center justify-center p-4 overflow-y-auto" onClick={onClose}>
            <div
                onClick={(e) => e.stopPropagation()}
                className="bg-white dark:bg-stone-900 rounded-lg w-full max-w-md border border-gray-200 dark:border-stone-700"
            >
                <div className="p-4 border-b border-gray-200 dark:border-stone-700 flex justify-between items-center">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-stone-100">
                        ✏️ {t('audio.edit.title')}
                    </h3>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700 dark:text-stone-400 dark:hover:text-stone-200 text-xl cursor-pointer">✕</button>
                </div>
                <div className="p-4 space-y-4">
                    {(audio.status === 'approved' || audio.status === 'rejected') && (
                        <div className="text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded p-2">
                            ℹ {t('audio.edit.warningRePending')}
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
                            disabled={saving || !dirty || !title.trim()}
                            className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50"
                        >
                            {saving ? t('audio.edit.saving') : t('audio.edit.saveBtn')}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
