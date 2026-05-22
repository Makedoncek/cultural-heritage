import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import {visitsService} from '../../services/visits.service';
import type {Visit} from '../../types/visits';

interface Props {
    username: string;
    onCountChange?: (count: number) => void;
}

export default function AuthorVisitsTab({username, onCountChange}: Props) {
    const {i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const [visits, setVisits] = useState<Visit[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        visitsService.listPublic(username)
            .then(data => { setVisits(data); onCountChange?.(data.length); })
            .catch(() => setError('Не вдалося завантажити публічні візити.'))
            .finally(() => setLoading(false));
    }, [username, onCountChange]);

    if (loading) return <div className="flex justify-center py-8"><div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/></div>;
    if (error) return <p className="text-red-600 text-center py-6">{error}</p>;
    if (visits.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500 dark:text-stone-400">У користувача поки немає публічних візитів.</p>
            </div>
        );
    }

    return (
        <>
            <p className="text-sm text-gray-700 dark:text-stone-200 mb-3">
                Відвідано публічно: <strong className="text-amber-700 dark:text-amber-400">{visits.length}</strong>
            </p>
            <div className="space-y-2">
                {visits.map(v => (
                    <div key={v.id} className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3">
                        <Link to={`/objects/${v.object_id}`} className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300">
                            {v.object_title}
                        </Link>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-stone-400">
                            {v.object_tags.length > 0 && (
                                <span>{v.object_tags.map(tag => tag.icon).join(' ')}</span>
                            )}
                            <span>{new Date(v.visited_at).toLocaleDateString(dateLocale)}</span>
                        </div>
                        {v.impression && (
                            <p className="text-sm text-gray-700 dark:text-stone-200 italic mt-2">
                                «{v.impression}»
                            </p>
                        )}
                    </div>
                ))}
            </div>
        </>
    );
}
