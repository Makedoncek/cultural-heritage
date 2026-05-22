import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import {usersService} from '../../services/users.service';
import type {AuthorProfile} from '../../types';

interface Props {
    onCountChange?: (count: number) => void;
}

export default function FavoriteAuthorsTab({onCountChange}: Props) {
    const {t} = useTranslation();
    const [authors, setAuthors] = useState<AuthorProfile[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        usersService.getFavoriteAuthors()
            .then(data => { setAuthors(data); onCountChange?.(data.length); })
            .catch(() => setError(t('subscriptions.loadError')))
            .finally(() => setLoading(false));
    }, [t, onCountChange]);

    const handleUnfollow = async (username: string) => {
        await usersService.toggleFollow(username);
        setAuthors(prev => {
            const next = prev.filter(a => a.username !== username);
            onCountChange?.(next.length);
            return next;
        });
    };

    if (loading) return <div className="flex justify-center py-8"><div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/></div>;
    if (error) return <p className="text-red-600 text-center py-6">{error}</p>;
    if (authors.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500 dark:text-stone-400">{t('subscriptions.empty')}</p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {authors.map(author => (
                <div
                    key={author.username}
                    className="flex items-center justify-between border border-gray-200 dark:border-stone-700 bg-white dark:bg-stone-900 rounded-lg px-4 py-3"
                >
                    <div>
                        <Link
                            to={`/authors/${author.username}`}
                            className="text-gray-900 dark:text-stone-100 font-medium hover:text-amber-700 dark:hover:text-amber-400"
                        >
                            {author.username}
                        </Link>
                        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-stone-400 mt-1">
                            <span>{t('subscriptions.objectsCount', {count: author.approved_objects_count})}</span>
                            <span>{t('subscriptions.followersCount', {count: author.followers_count})}</span>
                        </div>
                    </div>
                    <button
                        onClick={() => handleUnfollow(author.username)}
                        className="px-3 py-1.5 text-sm bg-gray-200 dark:bg-stone-800 text-gray-700 dark:text-stone-200 rounded-lg hover:bg-gray-300 dark:hover:bg-stone-700 cursor-pointer"
                    >
                        {t('subscriptions.unfollow')}
                    </button>
                </div>
            ))}
        </div>
    );
}
