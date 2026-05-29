import {useTranslation} from 'react-i18next';

interface TypeFilterProps {
    value: string;
    onChange: (value: string) => void;
}

export default function TypeFilter({value, onChange}: Readonly<TypeFilterProps>) {
    const {t} = useTranslation();
    const options = [
        {value: 'all', label: t('home.filters.typeAll')},
        {value: 'permanent', label: t('home.filters.typeMonuments')},
        {value: 'event', label: t('home.filters.typeEvents')},
    ];

    return (
        <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-stone-200 mb-2">{t('home.filters.typeTitle')}</h3>
            <div className="flex gap-1">
                {options.map(opt => (
                    <button
                        key={opt.value}
                        onClick={() => onChange(opt.value)}
                        className={`flex-1 px-2 py-1.5 text-xs rounded-lg font-medium transition-colors cursor-pointer ${
                            value === opt.value
                                ? 'bg-amber-600 dark:bg-amber-500 text-white dark:text-stone-900'
                                : 'bg-gray-100 dark:bg-stone-800 text-gray-600 dark:text-stone-300 hover:bg-gray-200 dark:hover:bg-stone-700'
                        }`}
                    >
                        {opt.label}
                    </button>
                ))}
            </div>
        </div>
    );
}
