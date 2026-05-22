import {useState} from 'react';
import {useAuth} from '../../context/AuthContext';
import ReportInaccuracyModal from './ReportInaccuracyModal';

interface Props {
    objectId: number;
    objectTitle: string;
}

export default function ReportInaccuracyButton({objectId, objectTitle}: Props) {
    const {isAuthenticated} = useAuth();
    const [open, setOpen] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    if (!isAuthenticated) return null;

    return (
        <>
            <button
                type="button"
                onClick={() => setOpen(true)}
                disabled={submitted}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-amber-300 dark:border-stone-600 bg-amber-50 dark:bg-stone-800 text-amber-800 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-stone-700 hover:border-amber-400 dark:hover:border-amber-500 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                title="Повідомити про помилку у даних"
            >
                <span className="text-base">⚠</span>
                {submitted ? 'Репорт надіслано' : 'Повідомити про неточність'}
            </button>
            {open && (
                <ReportInaccuracyModal
                    objectId={objectId}
                    objectTitle={objectTitle}
                    onClose={() => setOpen(false)}
                    onSubmitted={() => setSubmitted(true)}
                />
            )}
        </>
    );
}
