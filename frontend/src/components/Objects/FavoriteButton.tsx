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

        // Optimistic update
        setIsFavorited(!isFavorited);
        setCount(prev => isFavorited ? prev - 1 : prev + 1);

        try {
            const result = await objectsService.toggleFavorite(objectId);
            setIsFavorited(result.is_favorited);
            setCount(result.favorites_count);
            onToggle?.(result.is_favorited);
        } catch {
            // Revert on error
            setIsFavorited(isFavorited);
            setCount(count);
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
                    ? 'bg-red-50 text-red-600 hover:bg-red-100 border border-red-200'
                    : 'bg-gray-50 text-gray-500 hover:bg-gray-100 border border-gray-200'
            }`}
            title={isFavorited ? 'Видалити з обраного' : 'Додати до обраного'}
        >
            <span className="text-base">{isFavorited ? '❤️' : '🤍'}</span>
            {count > 0 && <span>{count}</span>}
        </button>
    );
}
