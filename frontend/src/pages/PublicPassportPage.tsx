import {useEffect, useState} from 'react';
import {Link, useParams} from 'react-router';
import {useTranslation} from 'react-i18next';
import {visitsService} from '../services/visits.service';
import type {Visit} from '../types/visits';

export default function PublicPassportPage() {
    const {username} = useParams<{username: string}>();
    const {t, i18n} = useTranslation();
    const dateLocale = i18n.language === 'en' ? 'en-GB' : 'uk-UA';
    const [visits, setVisits] = useState<Visit[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!username) return;
        visitsService.listPublic(username)
            .then(setVisits)
            .catch(() => setError('Не вдалося завантажити паспорт.'))
            .finally(() => setLoading(false));
    }, [username]);

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

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6">
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-1">
                    <Link to={`/authors/${username}`} className="hover:text-amber-700 dark:hover:text-amber-300">
                        ← {username}
                    </Link>
                </p>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100 mb-2">
                    🎒 Паспорт користувача @{username}
                </h1>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-6">
                    Публічні візити користувача. Тільки візити з ввімкненою опцією 🌐 публічно.
                </p>

                {visits.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500 dark:text-stone-400">
                            У користувача поки немає публічних візитів.
                        </p>
                    </div>
                ) : (
                    <>
                        <p className="text-sm text-gray-700 dark:text-stone-200 mb-3">
                            Відвідано публічно: <strong className="text-amber-700 dark:text-amber-400">{visits.length}</strong>
                        </p>
                        <div className="space-y-2">
                            {visits.map(v => (
                                <div
                                    key={v.id}
                                    className="border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                                >
                                    <Link to={`/objects/${v.object_id}`}
                                          className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-300">
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
                )}
            </div>
        </div>
    );
}
