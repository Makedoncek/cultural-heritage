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
                className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-stone-400 hover:text-amber-700 dark:hover:text-amber-300 underline decoration-dotted cursor-pointer disabled:opacity-50"
                title="Повідомити про помилку у даних"
            >
                ⚠ {submitted ? 'Репорт надіслано' : 'Повідомити про неточність'}
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
