import {useState} from 'react';
import toast from 'react-hot-toast';
import {plannedVisitsService} from '../../services/visits.service';
import {useAuth} from '../../context/AuthContext';

interface Props {
    objectId: number;
    isPlanned: boolean;
    onChange: (isPlanned: boolean) => void;
}

export default function PlanVisitToggleButton({objectId, isPlanned, onChange}: Readonly<Props>) {
    const {isAuthenticated} = useAuth();
    const [loading, setLoading] = useState(false);

    if (!isAuthenticated) return null;

    const handleToggle = async () => {
        setLoading(true);
        try {
            const result = await plannedVisitsService.toggle(objectId);
            onChange(result.is_planned);
            toast.success(result.is_planned ? '📌 Додано в плани' : 'Прибрано з планів');
        } catch {
            toast.error('Не вдалося оновити план');
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
                isPlanned
                    ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700 hover:bg-blue-200 dark:hover:bg-blue-900/60'
                    : 'bg-gray-50 dark:bg-stone-800 text-gray-700 dark:text-stone-200 border border-gray-300 dark:border-stone-600 hover:bg-gray-100 dark:hover:bg-stone-700'
            }`}
        >
            <span className="text-base">📌</span>
            {isPlanned ? 'У планах' : 'Планую відвідати'}
        </button>
    );
}
