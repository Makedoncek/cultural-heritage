import {useState, useEffect} from 'react';
import {useTranslation} from 'react-i18next';
import toast from 'react-hot-toast';
import {AxiosError} from 'axios';
import type {ContentLanguage} from './ContentLanguageSelector';

interface Props {
    open: boolean;
    onClose: () => void;
    /** Languages selectable as proposal targets (all supported, original included). */
    targetOptions: ContentLanguage[];
    /** The content's original language — marked with a "(original)" suffix in the picker. */
    originalLanguage?: ContentLanguage;
    onSubmit: (payload: {language: string; title: string; description: string}) => Promise<void>;
}

const LANGUAGE_LABELS: Record<string, string> = {
    uk: 'Українська',
    en: 'English',
    pl: 'Polski',
    de: 'Deutsch',
};

export default function TranslationSubmitModal({open, onClose, targetOptions, originalLanguage, onSubmit}: Props) {
    const {t} = useTranslation();
    const [language, setLanguage] = useState<ContentLanguage>(targetOptions[0] ?? 'en');
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (open) {
            setLanguage(targetOptions[0] ?? 'en');
            setTitle('');
            setDescription('');
        }
    }, [open, targetOptions]);

    useEffect(() => {
        if (!open) return;
        const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [open, onClose]);

    if (!open) return null;

    const handleSubmit = async () => {
        if (!title.trim()) {
            toast.error(t('translations.errorTitleRequired'));
            return;
        }
        setSubmitting(true);
        try {
            await onSubmit({language, title: title.trim(), description: description.trim()});
            toast.success(t('translations.submitted'));
            onClose();
        } catch (err) {
            const status = (err as AxiosError)?.response?.status;
            const detail = ((err as AxiosError)?.response?.data as {detail?: string} | undefined)?.detail;
            if (status === 409) {
                toast.error(detail ?? t('translations.errorPending'));
            } else if (status === 400) {
                toast.error(detail ?? t('translations.errorBadRequest'));
            } else {
                toast.error(t('translations.errorGeneric'));
            }
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[9999] bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
            <div
                className="bg-white dark:bg-stone-900 rounded-xl shadow-xl w-full max-w-lg p-5"
                onClick={e => e.stopPropagation()}
            >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-stone-100 mb-1">
                    ✍ {t('translations.modalTitleGeneric')}
                </h3>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-2">
                    {t('translations.modalHint')}
                </p>
                <p className="text-sm text-amber-700 dark:text-amber-400 mb-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 rounded-lg px-3 py-2">
                    {t('translations.ownContentNote')}
                </p>

                <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                    {t('translations.fieldLanguage')}
                </label>
                <select
                    value={language}
                    onChange={e => setLanguage(e.target.value as ContentLanguage)}
                    className="w-full mb-3 px-3 py-2 border border-gray-300 dark:border-stone-600 rounded-lg bg-white dark:bg-stone-800 text-gray-900 dark:text-stone-100"
                >
                    {targetOptions.map(l => (
                        <option key={l} value={l}>
                            {(LANGUAGE_LABELS[l] ?? l) + (l === originalLanguage ? t('translations.originalSuffix') : '')}
                        </option>
                    ))}
                </select>

                <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                    {t('translations.fieldTitle')}
                </label>
                <input
                    type="text"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    maxLength={200}
                    className="w-full mb-3 px-3 py-2 border border-gray-300 dark:border-stone-600 rounded-lg bg-white dark:bg-stone-800 text-gray-900 dark:text-stone-100"
                />

                <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                    {t('translations.fieldDescription')}
                </label>
                <textarea
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    rows={6}
                    className="w-full mb-4 px-3 py-2 border border-gray-300 dark:border-stone-600 rounded-lg bg-white dark:bg-stone-800 text-gray-900 dark:text-stone-100 resize-y"
                />

                <div className="flex justify-end gap-2">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={submitting}
                        className="px-3 py-1.5 text-sm border border-gray-300 dark:border-stone-600 text-gray-700 dark:text-stone-200 rounded-lg hover:bg-gray-50 dark:hover:bg-stone-800 cursor-pointer disabled:opacity-50"
                    >
                        {t('form.cancel')}
                    </button>
                    <button
                        type="button"
                        onClick={handleSubmit}
                        disabled={submitting || targetOptions.length === 0}
                        className="px-3 py-1.5 text-sm bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50"
                    >
                        {submitting ? t('translations.submitting') : t('translations.submit')}
                    </button>
                </div>
            </div>
        </div>
    );
}
