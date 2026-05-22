import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {reportsService} from '../../services/reports.service';
import type {InaccuracyReport, ReportStatus} from '../../types/reports';

const STATUS_BADGE: Record<ReportStatus, string> = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    resolved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    dismissed: 'bg-gray-100 text-gray-600 dark:bg-stone-800 dark:text-stone-400',
};

interface Props {
    onCountChange?: (count: number) => void;
}

export default function MyReportsTab({onCountChange}: Props) {
    const {i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const [reports, setReports] = useState<InaccuracyReport[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        reportsService.listMine()
            .then(data => { setReports(data); onCountChange?.(data.length); })
            .catch(() => setError('Не вдалося завантажити список.'))
            .finally(() => setLoading(false));
    }, [onCountChange]);

    const handleDelete = async (id: number) => {
        if (!confirm('Видалити цей репорт?')) return;
        try {
            await reportsService.deleteOwn(id);
            setReports(prev => {
                const next = prev.filter(r => r.id !== id);
                onCountChange?.(next.length);
                return next;
            });
            toast.success('Репорт видалено');
        } catch {
            toast.error('Не вдалося видалити');
        }
    };

    if (loading) return <div className="flex justify-center py-8"><div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/></div>;
    if (error) return <p className="text-red-600 text-center py-6">{error}</p>;
    if (reports.length === 0) {
        return <div className="text-center py-12"><p className="text-gray-500 dark:text-stone-400">Ви ще не надсилали репортів.</p></div>;
    }

    return (
        <div className="space-y-3">
            {reports.map(r => (
                <div key={r.id} className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                        <Link to={`/objects/${r.object_id}`} className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300">
                            {r.object_title}
                        </Link>
                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${STATUS_BADGE[r.status]}`}>{r.status_label}</span>
                    </div>
                    <p className="text-sm text-gray-700 dark:text-stone-200 mb-1">
                        <span className="text-gray-500 dark:text-stone-400">Причина:</span> {r.reason_label}
                    </p>
                    {r.note && <p className="text-sm text-gray-600 dark:text-stone-300 italic mb-1">«{r.note}»</p>}
                    {r.admin_response && (
                        <div className="mt-2 px-3 py-2 bg-amber-50 dark:bg-stone-800 border-l-2 border-amber-400 rounded text-sm">
                            <span className="text-gray-500 dark:text-stone-400 text-xs">Відповідь адміністратора:</span>
                            <p className="text-gray-700 dark:text-stone-200">{r.admin_response}</p>
                        </div>
                    )}
                    <div className="flex items-center justify-between mt-2 text-xs text-gray-500 dark:text-stone-400">
                        <span>{new Date(r.created_at).toLocaleDateString(dateLocale)}</span>
                        {r.status === 'pending' && (
                            <button onClick={() => handleDelete(r.id)} className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 cursor-pointer">
                                Видалити
                            </button>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}
