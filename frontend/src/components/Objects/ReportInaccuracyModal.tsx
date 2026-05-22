import {useState} from 'react';
import {useTranslation} from 'react-i18next';
import toast from 'react-hot-toast';
import {AxiosError} from 'axios';
import {reportsService} from '../../services/reports.service';
import type {ReportReasonType} from '../../types/reports';

interface Props {
    objectId: number;
    objectTitle: string;
    onClose: () => void;
    onSubmitted: () => void;
}

const REASONS: {value: ReportReasonType; label: string}[] = [
    {value: 'wrong_coords', label: 'Невірні координати'},
    {value: 'wrong_name', label: 'Неточна назва'},
    {value: 'wrong_description', label: 'Помилки в описі'},
    {value: 'wrong_tags', label: 'Невірні теги'},
    {value: 'duplicate', label: 'Дублікат іншого об\'єкта'},
    {value: 'other', label: 'Інше'},
];

export default function ReportInaccuracyModal({objectId, objectTitle, onClose, onSubmitted}: Props) {
    const {t} = useTranslation();
    const [reason, setReason] = useState<ReportReasonType>('wrong_coords');
    const [note, setNote] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const isDuplicate = reason === 'duplicate';
    const minNote = isDuplicate ? 5 : 0;
    const noteTooShort = note.trim().length < minNote;

    const handleSubmit = async () => {
        if (noteTooShort) return;
        setSubmitting(true);
        try {
            await reportsService.create(objectId, {reason_type: reason, note: note.trim()});
            toast.success('Репорт надіслано на модерацію');
            onSubmitted();
            onClose();
        } catch (err) {
            const axErr = err as AxiosError<{detail?: string}>;
            const msg = axErr.response?.data?.detail
                ?? (axErr.response?.status === 429 ? 'Ви вже надсилали репорт нещодавно.' : 'Не вдалося надіслати репорт');
            toast.error(msg);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[9999] bg-black/60 flex items-center justify-center px-4">
            <div className="bg-white dark:bg-stone-900 border border-gray-200 dark:border-stone-700 rounded-2xl shadow-xl max-w-md w-full p-6">
                <h3 className="text-lg font-bold text-gray-900 dark:text-stone-100 mb-1">
                    Повідомити про неточність
                </h3>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-4 truncate">
                    Об'єкт: <strong className="text-gray-700 dark:text-stone-200">{objectTitle}</strong>
                </p>

                <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                    Тип проблеми *
                </label>
                <select
                    value={reason}
                    onChange={(e) => setReason(e.target.value as ReportReasonType)}
                    className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                    {REASONS.map(r => (
                        <option key={r.value} value={r.value}>{r.label}</option>
                    ))}
                </select>

                <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                    Деталі {isDuplicate && <span className="text-red-500">*</span>}
                </label>
                <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    maxLength={500}
                    rows={4}
                    placeholder={
                        isDuplicate
                            ? 'Вкажіть посилання або назву оригінального об\'єкта'
                            : 'Опційно: опишіть проблему детальніше'
                    }
                    className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 placeholder-gray-400 dark:placeholder-stone-500 rounded-lg px-3 py-2 mb-1 focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
                />
                <p className="text-xs text-gray-500 dark:text-stone-400 mb-4 text-right">
                    {note.length} / 500
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
                        title={noteTooShort ? 'Для дублікатів — додайте посилання у деталях' : undefined}
                    >
                        {submitting ? 'Надсилання...' : 'Надіслати'}
                    </button>
                </div>
            </div>
        </div>
    );
}
