import {useState} from 'react';
import toast from 'react-hot-toast';
import {visitsService} from '../../services/visits.service';
import type {Visit} from '../../types/visits';

interface Props {
    visit: Visit;
    onClose: () => void;
    onUpdated: (updated: Visit) => void;
}

// Convert ISO datetime to the local-time string that <input type="datetime-local"> expects.
function toLocalInputValue(iso: string): string {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function nowLocalInputValue(): string {
    return toLocalInputValue(new Date().toISOString());
}

export default function VisitImpressionModal({visit, onClose, onUpdated}: Props) {
    const [impression, setImpression] = useState(visit.impression);
    const [visitedAt, setVisitedAt] = useState(toLocalInputValue(visit.visited_at));
    const [isPublic, setIsPublic] = useState(visit.is_public);
    const [saving, setSaving] = useState(false);

    const nowLocal = nowLocalInputValue();
    const futureDate = visitedAt > nowLocal;

    const handleSave = async () => {
        if (futureDate) {
            toast.error('Дата візиту не може бути у майбутньому');
            return;
        }
        setSaving(true);
        try {
            // The <input type="datetime-local"> returns 'YYYY-MM-DDTHH:mm' (no timezone).
            // Treat it as local time and serialize to ISO with timezone info.
            const updated = await visitsService.update(visit.id, {
                impression: impression.trim(),
                visited_at: new Date(visitedAt).toISOString(),
                is_public: isPublic,
            });
            onUpdated(updated);
            toast.success('Збережено');
            onClose();
        } catch {
            toast.error('Не вдалося зберегти');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[9999] bg-black/60 flex items-center justify-center px-4">
            <div className="bg-white dark:bg-stone-900 border border-gray-200 dark:border-stone-700 rounded-2xl shadow-xl max-w-md w-full p-6">
                <h3 className="text-lg font-bold text-gray-900 dark:text-stone-100 mb-1">
                    Враження від візиту
                </h3>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-4 truncate">
                    {visit.object_title}
                </p>

                <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                    Дата і час візиту
                </label>
                <input
                    type="datetime-local"
                    value={visitedAt}
                    max={nowLocal}
                    onChange={(e) => setVisitedAt(e.target.value)}
                    className={`w-full bg-white dark:bg-stone-800 border ${
                        futureDate ? 'border-red-400 dark:border-red-600' : 'border-gray-200 dark:border-stone-700'
                    } text-gray-900 dark:text-stone-100 rounded-lg px-3 py-2 mb-1 focus:outline-none focus:ring-2 focus:ring-amber-400`}
                />
                {futureDate && (
                    <p className="text-red-600 dark:text-red-400 text-xs mb-3">
                        Дата візиту не може бути у майбутньому
                    </p>
                )}
                {!futureDate && <div className="mb-3"/>}

                <label className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                    Враження
                </label>
                <textarea
                    value={impression}
                    onChange={(e) => setImpression(e.target.value)}
                    maxLength={1000}
                    rows={5}
                    placeholder="Що запам'яталось? Поради іншим відвідувачам?"
                    className="w-full bg-white dark:bg-stone-800 border border-gray-200 dark:border-stone-700 text-gray-900 dark:text-stone-100 placeholder-gray-400 dark:placeholder-stone-500 rounded-lg px-3 py-2 mb-1 focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
                />
                <p className="text-xs text-gray-500 dark:text-stone-400 mb-4 text-right">
                    {impression.length} / 1000
                </p>

                <label className="flex items-center gap-2 mb-4 cursor-pointer text-sm text-gray-700 dark:text-stone-200">
                    <input
                        type="checkbox"
                        checked={isPublic}
                        onChange={(e) => setIsPublic(e.target.checked)}
                        className="w-4 h-4 accent-amber-500 cursor-pointer"
                    />
                    {isPublic
                        ? <span><strong>🌐 Публічно</strong> — видно у публічному паспорті</span>
                        : <span><strong>🔒 Приватно</strong> — тільки для вас</span>}
                </label>

                <div className="flex gap-2 justify-end">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={saving}
                        className="px-4 py-2 text-sm border border-gray-300 dark:border-stone-600 text-gray-700 dark:text-stone-200 rounded-lg hover:bg-gray-50 dark:hover:bg-stone-800 cursor-pointer disabled:opacity-50"
                    >
                        Скасувати
                    </button>
                    <button
                        type="button"
                        onClick={handleSave}
                        disabled={saving || futureDate}
                        className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 rounded-lg cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {saving ? 'Збереження...' : 'Зберегти'}
                    </button>
                </div>
            </div>
        </div>
    );
}
