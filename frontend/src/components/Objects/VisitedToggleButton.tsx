import {useState} from 'react';
import toast from 'react-hot-toast';
import {visitsService} from '../../services/visits.service';
import {useAuth} from '../../context/AuthContext';
import type {Visit} from '../../types/visits';

interface Props {
    objectId: number;
    isVisited: boolean;
    onChange: (isVisited: boolean, visit?: Visit) => void;
}

export default function VisitedToggleButton({objectId, isVisited, onChange}: Readonly<Props>) {
    const {isAuthenticated} = useAuth();
    const [loading, setLoading] = useState(false);

    if (!isAuthenticated) return null;

    const handleToggle = async () => {
        setLoading(true);
        try {
            const result = await visitsService.toggle(objectId);
            onChange(result.is_visited, result.visit);
            toast.success(result.is_visited ? '✓ Додано до відвіданих' : 'Прибрано з відвіданих');
        } catch {
            toast.error('Не вдалося оновити статус візиту');
        } finally {
            setLoading(false);
        }
    };

    return (
        <button
            type="button"
            onClick={handleToggle}
            disabled={loading}
            className={`inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50 ${
                isVisited
                    ? 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-300 border border-green-300 dark:border-green-700 hover:bg-green-200 dark:hover:bg-green-900/60'
                    : 'bg-gray-50 dark:bg-stone-800 text-gray-700 dark:text-stone-200 border border-gray-300 dark:border-stone-600 hover:bg-gray-100 dark:hover:bg-stone-700'
            }`}
        >
            <span className="text-base">{isVisited ? '✓' : '📍'}</span>
            {isVisited ? 'Відвідано' : 'Я тут був'}
        </button>
    );
}
