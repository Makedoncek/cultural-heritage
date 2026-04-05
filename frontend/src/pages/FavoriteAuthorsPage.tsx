import {useState, useEffect} from 'react';
import {Link} from 'react-router';
import {usersService} from '../services/users.service';
import type {AuthorProfile} from '../types';

export default function FavoriteAuthorsPage() {
    const [authors, setAuthors] = useState<AuthorProfile[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        usersService.getFavoriteAuthors()
            .then(data => setAuthors(data))
            .catch(() => setError('Не вдалося завантажити підписки.'))
            .finally(() => setLoading(false));
    }, []);

    const handleUnfollow = async (username: string) => {
        await usersService.toggleFollow(username);
        setAuthors(prev => prev.filter(a => a.username !== username));
    };

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent"/>
                    <p className="text-gray-600">Завантаження...</p>
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
            <div className="max-w-2xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Підписки</h1>
                <p className="text-gray-500 text-sm mb-6">Автори, на яких ви підписані</p>

                {authors.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500">Ви ще не підписані на жодного автора</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {authors.map(author => (
                            <div
                                key={author.username}
                                className="flex items-center justify-between border border-gray-200 rounded-lg px-4 py-3"
                            >
                                <div>
                                    <Link
                                        to={`/authors/${author.username}`}
                                        className="text-gray-900 font-medium hover:text-amber-700"
                                    >
                                        {author.username}
                                    </Link>
                                    <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
                                        <span>{author.approved_objects_count} об'єктів</span>
                                        <span>{author.followers_count} підписників</span>
                                    </div>
                                </div>
                                <button
                                    onClick={() => handleUnfollow(author.username)}
                                    className="px-3 py-1.5 text-sm bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 cursor-pointer"
                                >
                                    Відписатися
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
