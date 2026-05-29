import {useState} from 'react';
import {useTranslation} from 'react-i18next';
import {useAuth} from '../../context/AuthContext';
import ReportInaccuracyModal from './ReportInaccuracyModal';
import type {ReportTargetType} from '../../types/reports';

interface Props {
    targetType: ReportTargetType;
    targetId: number;
    targetTitle: string;
    /** Compact icon-only style for inline placement (photo/audio cards). */
    compact?: boolean;
}

export default function ReportInaccuracyButton({targetType, targetId, targetTitle, compact}: Readonly<Props>) {
    const {t} = useTranslation();
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
                className={compact
                    ? 'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-lg border border-amber-300 dark:border-stone-600 bg-amber-50 dark:bg-stone-800 text-amber-800 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-stone-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed'
                    : 'inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-amber-300 dark:border-stone-600 bg-amber-50 dark:bg-stone-800 text-amber-800 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-stone-700 hover:border-amber-400 dark:hover:border-amber-500 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed'}
                title={t('reports.buttonTitle')}
            >
                <span className="text-base">⚠</span>
                {compact
                    ? (submitted ? t('reports.sentShort') : t('reports.report'))
                    : (submitted ? t('reports.sent') : t('reports.button'))}
            </button>
            {open && (
                <ReportInaccuracyModal
                    targetType={targetType}
                    targetId={targetId}
                    targetTitle={targetTitle}
                    onClose={() => setOpen(false)}
                    onSubmitted={() => setSubmitted(true)}
                />
            )}
        </>
    );
}
