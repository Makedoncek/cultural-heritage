import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import {reportsService} from '../services/reports.service';
import type {InaccuracyReport, ReportStatus} from '../types/reports';

const STATUS_BADGE: Record<ReportStatus, string> = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    resolved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    dismissed: 'bg-gray-100 text-gray-600 dark:bg-stone-800 dark:text-stone-400',
};

export default function ReportsOnMyObjectsPage() {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const [reports, setReports] = useState<InaccuracyReport[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        reportsService.listOnMyObjects()
            .then(setReports)
            .catch(() => setError('Не вдалося завантажити список.'))
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
                    <p className="text-gray-600 dark:text-stone-300">{t('home.loading')}</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <p className="text-red-600">{error}</p>
            </div>
        );
    }

    const pending = reports.filter(r => r.status === 'pending');
    const resolved = reports.filter(r => r.status !== 'pending');

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100 mb-2">
                    Репорти на мої об'єкти
                </h1>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-6">
                    Звіти про неточності, які користувачі надіслали для ваших об'єктів. Адміністратор приймає рішення про підтвердження.
                </p>

                {reports.length === 0 && (
                    <div className="text-center py-12">
                        <p className="text-gray-500 dark:text-stone-400">Поки що жодного репорту.</p>
                    </div>
                )}

                {pending.length > 0 && (
                    <>
                        <h2 className="text-sm font-semibold text-gray-700 dark:text-stone-200 mb-2 uppercase tracking-wide">
                            На розгляді ({pending.length})
                        </h2>
                        <div className="space-y-3 mb-6">
                            {pending.map(r => (
                                <ReportCard key={r.id} report={r} dateLocale={dateLocale}/>
                            ))}
                        </div>
                    </>
                )}

                {resolved.length > 0 && (
                    <>
                        <h2 className="text-sm font-semibold text-gray-700 dark:text-stone-200 mb-2 uppercase tracking-wide">
                            Опрацьовано ({resolved.length})
                        </h2>
                        <div className="space-y-3">
                            {resolved.map(r => (
                                <ReportCard key={r.id} report={r} dateLocale={dateLocale}/>
                            ))}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

function ReportCard({report: r, dateLocale}: {report: InaccuracyReport; dateLocale: string}) {
    return (
        <div className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3">
            <div className="flex flex-wrap items-center gap-2 mb-2">
                <Link
                    to={`/objects/${r.object_id}`}
                    className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300"
                >
                    {r.object_title}
                </Link>
                <span className={`px-2 py-0.5 text-xs font-medium rounded ${STATUS_BADGE[r.status]}`}>
                    {r.status_label}
                </span>
            </div>
            <p className="text-sm text-gray-700 dark:text-stone-200 mb-1">
                <span className="text-gray-500 dark:text-stone-400">Причина:</span> {r.reason_label}
            </p>
            <p className="text-xs text-gray-500 dark:text-stone-400 mb-1">
                Користувач: <strong>@{r.reporter_username}</strong>
            </p>
            {r.note && (
                <p className="text-sm text-gray-600 dark:text-stone-300 italic">
                    «{r.note}»
                </p>
            )}
            {r.admin_response && (
                <div className="mt-2 px-3 py-2 bg-amber-50 dark:bg-stone-800 border-l-2 border-amber-400 rounded text-sm">
                    <span className="text-gray-500 dark:text-stone-400 text-xs">Відповідь адміністратора:</span>
                    <p className="text-gray-700 dark:text-stone-200">{r.admin_response}</p>
                </div>
            )}
            <p className="mt-2 text-xs text-gray-500 dark:text-stone-400">
                {new Date(r.created_at).toLocaleDateString(dateLocale)}
            </p>
        </div>
    );
}
