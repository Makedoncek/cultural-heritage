import {useTranslation} from 'react-i18next';

interface Props {
    show: boolean;
    loading: boolean;
    shown: number;
    total: number;
    onClick: () => void;
}

export default function LoadMoreButton({show, loading, shown, total, onClick}: Props) {
    const {t} = useTranslation();
    if (!show) return null;
    return (
        <div className="flex justify-center pt-3">
            <button
                type="button"
                onClick={onClick}
                disabled={loading}
                className="px-4 py-2 text-sm bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 rounded-lg hover:bg-amber-200 dark:hover:bg-amber-900/60 cursor-pointer disabled:opacity-50"
            >
                {loading ? t('common.loadingMore') : t('common.loadMore', {shown, total})}
            </button>
        </div>
    );
}
