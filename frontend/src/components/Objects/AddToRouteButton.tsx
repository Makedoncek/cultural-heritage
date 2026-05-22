import {useState, useEffect, useRef} from 'react';
import {useNavigate} from 'react-router';
import toast from 'react-hot-toast';
import {useTranslation} from 'react-i18next';
import {routesService} from '../../services/routes.service';
import type {RouteListItem} from '../../types/routes';

interface Props {
    objectId: number;
}

export default function AddToRouteButton({objectId}: Props) {
    const {t} = useTranslation();
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const [routes, setRoutes] = useState<RouteListItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [adding, setAdding] = useState<number | null>(null);
    const wrapRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        const onClickOutside = (e: MouseEvent) => {
            if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', onClickOutside);
        return () => document.removeEventListener('mousedown', onClickOutside);
    }, [open]);

    const openPicker = async () => {
        setOpen(true);
        if (routes.length > 0) return;
        setLoading(true);
        try {
            const data = await routesService.listMine();
            setRoutes(data.filter(r => r.status !== 'archived'));
        } catch {
            toast.error(t('routes.toast.loadFailed'));
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async (route: RouteListItem) => {
        setAdding(route.id);
        try {
            await routesService.addStop(route.id, {cultural_object: objectId});
            setRoutes(prev => prev.map(r =>
                r.id === route.id ? {...r, stops_count: r.stops_count + 1} : r,
            ));
            toast.success(t('routes.toast.stopAdded'));
            setOpen(false);
        } catch (e) {
            const detail = (e as {response?: {data?: {detail?: string}}}).response?.data?.detail;
            toast.error(detail || t('routes.toast.stopAddFailed'));
        } finally {
            setAdding(null);
        }
    };

    const handleCreateNew = () => {
        sessionStorage.setItem('routeFirstStopObjectId', String(objectId));
        navigate('/routes/add');
    };

    return (
        <div ref={wrapRef} className="relative inline-block">
            <button
                type="button"
                onClick={openPicker}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors cursor-pointer bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-400 text-white"
            >
                <span className="text-base">🗺</span>
                {t('object.addToRoute')}
            </button>

            {open && (
                <div className="absolute right-0 mt-2 w-72 max-h-96 overflow-y-auto bg-white dark:bg-stone-900 border border-gray-200 dark:border-stone-700 rounded-lg shadow-lg z-30">
                    <div className="p-2 border-b border-gray-100 dark:border-stone-700 text-xs text-gray-500 dark:text-stone-400 font-medium">
                        {t('object.pickRoute')}
                    </div>
                    {loading ? (
                        <div className="p-4 flex justify-center">
                            <div className="h-5 w-5 animate-spin rounded-full border-2 border-amber-500 border-t-transparent"/>
                        </div>
                    ) : routes.length === 0 ? (
                        <div className="p-3 text-sm text-gray-500 dark:text-stone-400">
                            {t('routes.emptyMine')}
                        </div>
                    ) : (
                        <ul className="py-1">
                            {routes.map(r => (
                                <li key={r.id}>
                                    <button
                                        type="button"
                                        onClick={() => handleAdd(r)}
                                        disabled={adding === r.id}
                                        className="w-full text-left px-3 py-2 text-sm hover:bg-amber-50 dark:hover:bg-stone-800 cursor-pointer disabled:opacity-50 flex justify-between items-center gap-2"
                                    >
                                        <span className="text-gray-900 dark:text-stone-100 truncate flex-1">
                                            {r.title}
                                        </span>
                                        <span className="text-xs text-gray-500 dark:text-stone-400 shrink-0">
                                            {r.stops_count} {t('routes.stops')}
                                        </span>
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}
                    <div className="border-t border-gray-100 dark:border-stone-700">
                        <button
                            type="button"
                            onClick={handleCreateNew}
                            className="w-full text-left px-3 py-2 text-sm text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-stone-800 cursor-pointer"
                        >
                            + {t('routes.createButton')}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
