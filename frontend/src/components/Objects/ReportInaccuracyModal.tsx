import {useState} from 'react';
import {useTranslation} from 'react-i18next';
import toast from 'react-hot-toast';
import {AxiosError} from 'axios';
import {reportsService} from '../../services/reports.service';
import {REASONS_BY_TARGET, type ReportReasonType, type ReportTargetType} from '../../types/reports';

interface Props {
    targetType: ReportTargetType;
    targetId: number;
    targetTitle: string;
    onClose: () => void;
    onSubmitted: () => void;
}

export default function ReportInaccuracyModal({targetType, targetId, targetTitle, onClose, onSubmitted}: Readonly<Props>) {
    const {t} = useTranslation();
    const reasons = REASONS_BY_TARGET[targetType];
    const [reason, setReason] = useState<ReportReasonType>(reasons[0]);
    const [note, setNote] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const isDuplicate = reason === 'duplicate';
    const minNote = isDuplicate ? 5 : 0;
    const noteTooShort = note.trim().length < minNote;

    const handleSubmit = async () => {
        if (noteTooShort) return;
        setSubmitting(true);
        try {
            await reportsService.create({target_type: targetType, target_id: targetId, reason_type: reason, note: note.trim()});
            toast.success(t('reports.submitted'));
            onSubmitted();
            onClose();
        } catch (err) {
            const axErr = err as AxiosError<{detail?: string}>;
            const msg = axErr.response?.data?.detail
                ?? (axErr.response?.status === 429 ? t('reports.throttled') : t('reports.submitError'));
            toast.error(msg);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[9999] bg-black/60 flex items-center justify-center px-4">
            <div className="bg-white dark:bg-stone-900 border border-gray-200 dark:border-stone-700 rounded-2xl shadow-xl max-w-md w-full p-6">
                <h3 className="text-lg font-bold text-gray-900 dark:text-stone-100 mb-1">
                    {t(`reports.modalTitleByType.${targetType}`)}
                </h3>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-2 truncate">
                    {t(`reports.targetType.${targetType}`)}: <strong className="text-gray-700 dark:text-stone-200">{targetTitle}</strong>
                </p>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-4">
                    {t(`reports.hintByType.${targetType}`)}
                </p>

                <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                    {t('reports.reasonLabel')} *
                </label>
                <select
                    value={reason}
                    onChange={(e) => setReason(e.target.value as ReportReasonType)}
                    className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                    {reasons.map(r => (
                        <option key={r} value={r}>{t(`reports.reason.${r}`)}</option>
                    ))}
                </select>

                <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                    {t('reports.detailsLabel')} {isDuplicate && <span className="text-red-500">*</span>}
                </label>
                <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    maxLength={2000}
                    rows={4}
                    placeholder={isDuplicate ? t('reports.duplicatePlaceholder') : t('reports.notePlaceholder')}
                    className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 placeholder-gray-400 dark:placeholder-stone-500 rounded-lg px-3 py-2 mb-1 focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
                />
                <p className="text-xs text-gray-500 dark:text-stone-400 mb-4 text-right">
                    {note.length} / 2000
                </p>

                <div className="flex gap-2 justify-end">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={submitting}
                        className="px-4 py-2 text-sm border border-gray-300 dark:border-stone-600 text-gray-700 dark:text-stone-200 rounded-lg hover:bg-gray-50 dark:hover:bg-stone-800 cursor-pointer disabled:opacity-50"
                    >
                        {t('form.cancel')}
                    </button>
                    <button
                        type="button"
                        onClick={handleSubmit}
                        disabled={submitting || noteTooShort}
                        className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50"
                    >
                        {submitting ? t('reports.submitting') : t('reports.submit')}
                    </button>
                </div>
            </div>
        </div>
    );
}
