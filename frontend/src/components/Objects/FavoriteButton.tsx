import {useState} from 'react';
import {objectsService} from '../../services/objects.service';
import toast from 'react-hot-toast';

interface FavoriteButtonProps {
    objectId: number;
    initialFavorited: boolean;
    initialCount: number;
    onToggle?: (isFavorited: boolean) => void;
}

export default function FavoriteButton({objectId, initialFavorited, initialCount, onToggle}: FavoriteButtonProps) {
    const [isFavorited, setIsFavorited] = useState(initialFavorited);
    const [count, setCount] = useState(initialCount);
    const [loading, setLoading] = useState(false);

    const handleToggle = async () => {
        if (loading) return;
        setLoading(true);

        const prevFavorited = isFavorited;
        const prevCount = count;

        // Optimistic update
        setIsFavorited(!prevFavorited);
        setCount(prevFavorited ? prevCount - 1 : prevCount + 1);

        try {
            const result = await objectsService.toggleFavorite(objectId);
            setIsFavorited(result.is_favorited);
            setCount(result.favorites_count);
            onToggle?.(result.is_favorited);
        } catch {
            // Revert on error
            setIsFavorited(prevFavorited);
            setCount(prevCount);
            toast.error('Не вдалося оновити обране');
        } finally {
            setLoading(false);
        }
    };

    return (
        <button
            onClick={handleToggle}
            disabled={loading}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                isFavorited
                    ? 'bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 border border-red-200 dark:border-red-800'
                    : 'bg-gray-50 dark:bg-stone-800 text-gray-500 dark:text-stone-300 hover:bg-gray-100 dark:hover:bg-stone-700 border border-gray-200 dark:border-stone-600'
            }`}
            title={isFavorited ? 'Видалити з обраного' : 'Додати до обраного'}
        >
            <span className="text-base">{isFavorited ? '❤️' : '🤍'}</span>
            {count > 0 && <span>{count}</span>}
        </button>
    );
}
