import {useCallback, useState, type ReactNode} from 'react';
import {useSearchParams} from 'react-router';
import {useTranslation} from 'react-i18next';
import FavoriteObjectsTab from '../components/Saved/FavoriteObjectsTab';
import FavoriteAuthorsTab from '../components/Saved/FavoriteAuthorsTab';

type Tab = 'objects' | 'authors';

export default function SavedPage() {
    const {t} = useTranslation();
    const [params, setParams] = useSearchParams();
    const initialTab: Tab = params.get('tab') === 'authors' ? 'authors' : 'objects';
    const [tab, setTab] = useState<Tab>(initialTab);
    const [objCount, setObjCount] = useState<number | null>(null);
    const [authorCount, setAuthorCount] = useState<number | null>(null);

    const onObjects = useCallback((n: number) => setObjCount(n), []);
    const onAuthors = useCallback((n: number) => setAuthorCount(n), []);

    const handleTabChange = (next: Tab) => {
        setTab(next);
        setParams({tab: next}, {replace: true});
    };

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100 mb-2">{t('saved.title')}</h1>
                <p className="text-sm text-gray-500 dark:text-stone-400 mb-6">{t('saved.subtitle')}</p>

                <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-stone-700">
                    <TabBtn active={tab === 'objects'} onClick={() => handleTabChange('objects')} count={objCount}>
                        ❤ {t('saved.tabObjects')}
                    </TabBtn>
                    <TabBtn active={tab === 'authors'} onClick={() => handleTabChange('authors')} count={authorCount}>
                        👤 {t('saved.tabAuthors')}
                    </TabBtn>
                </div>

                {tab === 'objects'
                    ? <FavoriteObjectsTab onCountChange={onObjects}/>
                    : <FavoriteAuthorsTab onCountChange={onAuthors}/>}
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

function TabBtn({active, onClick, count, children}: TabBtnProps) {
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
