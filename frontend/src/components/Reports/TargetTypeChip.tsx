import {useTranslation} from 'react-i18next';
import type {ReportTargetType} from '../../types/reports';

const CLS: Record<string, string> = {
    object: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border border-blue-200 dark:border-blue-800',
    route: 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300 border border-teal-200 dark:border-teal-800',
    photo: 'bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-900/40 dark:text-fuchsia-300 border border-fuchsia-200 dark:border-fuchsia-800',
    audio: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800',
    object_translation: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800',
    route_translation: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800',
};

const ICON: Record<string, string> = {
    object: '📍', route: '🗺', photo: '📷', audio: '🎧',
    object_translation: '✍', route_translation: '✍',
};

export default function TargetTypeChip({type}: Readonly<{type: ReportTargetType | null}>) {
    const {t} = useTranslation();
    if (!type) return null;
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full font-medium ${CLS[type] ?? CLS.object}`}>
            {ICON[type] ?? '📍'} {t(`reports.targetType.${type}`)}
        </span>
    );
}
