import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import toast from 'react-hot-toast';
import {visitsService, plannedVisitsService} from '../services/visits.service';
import type {Visit, PlannedVisit, VisitsStats} from '../types/visits';

export default function CulturalPassportPage() {
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const [visits, setVisits] = useState<Visit[]>([]);
    const [planned, setPlanned] = useState<PlannedVisit[]>([]);
    const [stats, setStats] = useState<VisitsStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        Promise.all([
            visitsService.listMine(),
            plannedVisitsService.listMine(),
            visitsService.stats(),
        ])
            .then(([v, p, s]) => {
                setVisits(v);
                setPlanned(p);
                setStats(s);
            })
            .catch(() => setError('Не вдалося завантажити паспорт.'))
            .finally(() => setLoading(false));
    }, []);

    const togglePublic = async (v: Visit) => {
        try {
            const updated = await visitsService.update(v.id, {is_public: !v.is_public});
            setVisits(prev => prev.map(x => x.id === v.id ? updated : x));
            toast.success(updated.is_public ? 'Тепер публічно' : 'Тепер приватно');
        } catch {
            toast.error('Не вдалося оновити');
        }
    };

    const convertToVisit = async (p: PlannedVisit) => {
        try {
            const result = await plannedVisitsService.convertToVisit(p.id);
            setPlanned(prev => prev.filter(x => x.id !== p.id));
            setVisits(prev => [result.visit, ...prev]);
            toast.success('Переміщено у відвідані');
        } catch {
            toast.error('Не вдалося конвертувати');
        }
    };

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

    const percent = stats && stats.total_approved_objects > 0
        ? (stats.total_visits / stats.total_approved_objects * 100).toFixed(2)
        : '0';

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100 mb-2">
                    🎒 Культурний паспорт
                </h1>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-6">
                    Ваші відвідані та заплановані культурні об'єкти України.
                </p>

                {/* Counters */}
                <div className="grid grid-cols-2 gap-3 mb-6">
                    <div className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-4">
                        <p className="text-xs text-gray-500 dark:text-stone-400 uppercase tracking-wide">📊 Відвідано</p>
                        <p className="text-3xl font-bold text-amber-700 dark:text-amber-400 mt-1">
                            {stats?.total_visits ?? 0}
                            <span className="text-base text-gray-500 dark:text-stone-400 font-normal ml-1">
                                з {stats?.total_approved_objects ?? 0} ({percent}%)
                            </span>
                        </p>
                    </div>
                    <div className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-4">
                        <p className="text-xs text-gray-500 dark:text-stone-400 uppercase tracking-wide">📌 У планах</p>
                        <p className="text-3xl font-bold text-blue-700 dark:text-blue-400 mt-1">
                            {planned.length}
                        </p>
                    </div>
                </div>

                {/* By tag */}
                {stats && stats.by_tag.length > 0 && (
                    <div className="mb-6 border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg p-4">
                        <h2 className="text-sm font-semibold text-gray-700 dark:text-stone-200 uppercase tracking-wide mb-2">
                            За тегами
                        </h2>
                        <div className="flex flex-wrap gap-2">
                            {stats.by_tag.map(tag => (
                                <span
                                    key={tag.id}
                                    className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 rounded-full text-sm"
                                >
                                    {tag.icon} {tag.name}
                                    <strong className="ml-1">{tag.visited_count}</strong>
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Visits list */}
                <h2 className="text-lg font-semibold text-gray-900 dark:text-stone-100 mb-3">
                    📋 Хронологія візитів ({visits.length})
                </h2>
                {visits.length === 0 ? (
                    <p className="text-gray-500 dark:text-stone-400 text-sm mb-6">
                        Ще немає відвіданих об'єктів. Відкрийте об'єкт на карті і натисніть «Я тут був».
                    </p>
                ) : (
                    <div className="space-y-2 mb-6">
                        {visits.map(v => (
                            <div
                                key={v.id}
                                className="flex items-center justify-between gap-2 border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                            >
                                <div className="flex-1 min-w-0">
                                    <Link to={`/objects/${v.object_id}`}
                                          className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300">
                                        {v.object_title}
                                    </Link>
                                    <p className="text-xs text-gray-500 dark:text-stone-400 mt-1">
                                        {new Date(v.visited_at).toLocaleDateString(dateLocale)}
                                        {v.impression && (
                                            <span className="ml-2 italic">«{v.impression}»</span>
                                        )}
                                    </p>
                                </div>
                                <button
                                    onClick={() => togglePublic(v)}
                                    className="text-lg cursor-pointer"
                                    title={v.is_public ? 'Публічно — клік щоб зробити приватним' : 'Приватно — клік щоб зробити публічним'}
                                >
                                    {v.is_public ? '🌐' : '🔒'}
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {/* Planned list */}
                <h2 className="text-lg font-semibold text-gray-900 dark:text-stone-100 mb-3">
                    📌 Плани ({planned.length})
                </h2>
                {planned.length === 0 ? (
                    <p className="text-gray-500 dark:text-stone-400 text-sm">
                        Поки що жодного плану. Додавайте об'єкти у плани через «Планую відвідати».
                    </p>
                ) : (
                    <div className="space-y-2">
                        {planned.map(p => (
                            <div
                                key={p.id}
                                className="flex items-center justify-between gap-2 border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                            >
                                <div className="flex-1 min-w-0">
                                    <Link to={`/objects/${p.object_id}`}
                                          className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300">
                                        {p.object_title}
                                    </Link>
                                    {p.planned_date && (
                                        <p className="text-xs text-gray-500 dark:text-stone-400 mt-1">
                                            план: {new Date(p.planned_date).toLocaleDateString(dateLocale)}
                                        </p>
                                    )}
                                </div>
                                <button
                                    onClick={() => convertToVisit(p)}
                                    className="px-3 py-1.5 text-xs bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-300 border border-green-300 dark:border-green-700 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/60 cursor-pointer"
                                >
                                    ✓ Відвідано
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
