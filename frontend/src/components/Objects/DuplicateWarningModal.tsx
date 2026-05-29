import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';

interface NearbyObject {
    id: number;
    title: string;
    distance_m: number;
}

interface Props {
    nearby: NearbyObject[];
    onCancel: () => void;
    onProceed: () => void;
    keyPrefix?: string;
}

export default function DuplicateWarningModal({nearby, onCancel, onProceed, keyPrefix = 'duplicateWarning'}: Props) {
    const {t} = useTranslation();
    const k = (key: string) => t(`${keyPrefix}.${key}`);
    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 overflow-y-auto">
            <button
                type="button"
                aria-label="Закрити"
                onClick={onCancel}
                className="absolute inset-0 bg-black/60 cursor-default"
            />
            <div className="relative bg-white dark:bg-stone-900 rounded-lg w-full max-w-md border border-gray-200 dark:border-stone-700">
                <div className="p-4 border-b border-gray-200 dark:border-stone-700">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-stone-100 flex items-center gap-2">
                        ⚠️ {k('title')}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-stone-300 mt-1">
                        {k('subtitle')}
                    </p>
                </div>

                <div className="p-4 max-h-80 overflow-y-auto">
                    <ul className="space-y-2">
                        {nearby.map(obj => (
                            <li key={obj.id}>
                                <Link
                                    to={`/objects/${obj.id}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center justify-between gap-3 px-3 py-2 border border-gray-200 dark:border-stone-700 rounded-lg hover:border-amber-400 dark:hover:border-amber-500 hover:bg-amber-50 dark:hover:bg-stone-800 transition-colors"
                                >
                                    <span className="text-gray-900 dark:text-stone-100 font-medium truncate">
                                        {obj.title}
                                    </span>
                                    <span className="text-xs text-gray-500 dark:text-stone-400 shrink-0">
                                        {obj.distance_m < 10
                                            ? k('veryClose')
                                            : t(`${keyPrefix}.distance`, {meters: Math.round(obj.distance_m)})}
                                    </span>
                                </Link>
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="p-4 border-t border-gray-200 dark:border-stone-700 flex justify-end gap-2">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="px-3 py-2 text-sm border border-gray-300 dark:border-stone-600 text-gray-700 dark:text-stone-200 rounded-lg hover:bg-gray-100 dark:hover:bg-stone-800 cursor-pointer"
                    >
                        {k('cancel')}
                    </button>
                    <button
                        type="button"
                        onClick={onProceed}
                        className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer"
                    >
                        {k('proceed')}
                    </button>
                </div>
            </div>
        </div>
    );
}
