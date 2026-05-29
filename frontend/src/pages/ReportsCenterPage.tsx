import {useCallback, useState, type ReactNode} from 'react';
import {useSearchParams} from 'react-router';
import {useTranslation} from 'react-i18next';
import MyReportsTab from '../components/Reports/MyReportsTab';
import ReportsOnMyObjectsTab from '../components/Reports/ReportsOnMyObjectsTab';

type Tab = 'mine' | 'on-mine';

export default function ReportsCenterPage() {
    const {t} = useTranslation();
    const [params, setParams] = useSearchParams();
    const initialTab: Tab = params.get('tab') === 'on-mine' ? 'on-mine' : 'mine';
    const [tab, setTab] = useState<Tab>(initialTab);
    const [mineCount, setMineCount] = useState<number | null>(null);
    const [onMineCount, setOnMineCount] = useState<number | null>(null);

    const handleTabChange = (next: Tab) => {
        setTab(next);
        setParams({tab: next}, {replace: true});
    };

    const onMineChange = useCallback((n: number) => setMineCount(n), []);
    const onOnMineChange = useCallback((n: number) => setOnMineCount(n), []);

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100 mb-2">
                    {t('reports.title')}
                </h1>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-6">
                    {t('reports.subtitle')}
                </p>

                <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-stone-700">
                    <TabBtn active={tab === 'mine'} onClick={() => handleTabChange('mine')} count={mineCount}>
                        📤 {t('reports.tabMine')}
                    </TabBtn>
                    <TabBtn active={tab === 'on-mine'} onClick={() => handleTabChange('on-mine')} count={onMineCount}>
                        📥 {t('reports.tabOnMine')}
                    </TabBtn>
                </div>

                {tab === 'mine'
                    ? <MyReportsTab onCountChange={onMineChange}/>
                    : <ReportsOnMyObjectsTab onCountChange={onOnMineChange}/>}
            </div>
        </div>
    );
}

interface TabBtnProps {
    active: boolean;
    onClick: () => void;
    count: number | null;
    children: ReactNode;
}

function TabBtn({active, onClick, count, children}: Readonly<TabBtnProps>) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors cursor-pointer ${
                active
                    ? 'border-amber-500 text-amber-700 dark:text-amber-400'
                    : 'border-transparent text-gray-500 dark:text-stone-400 hover:text-gray-700 dark:hover:text-stone-200'
            }`}
        >
            {children}
            {count !== null && (
                <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${active ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300' : 'bg-gray-100 dark:bg-stone-800 text-gray-600 dark:text-stone-400'}`}>
                    {count}
                </span>
            )}
        </button>
    );
}
