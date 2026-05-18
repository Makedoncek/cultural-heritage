import {useTranslation} from 'react-i18next';

interface EventStatusFilterProps {
    value: string;
    onChange: (value: string) => void;
}

export default function EventStatusFilter({value, onChange}: EventStatusFilterProps) {
    const {t} = useTranslation();
    const options = [
        {value: 'all', label: t('home.filters.eventStatusAll')},
        {value: 'active', label: t('home.filters.eventStatusActive')},
        {value: 'upcoming', label: t('home.filters.eventStatusUpcoming')},
    ];

    return (
        <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">{t('home.filters.eventStatusTitle')}</h3>
            <div className="flex gap-1">
                {options.map(opt => (
                    <button
                        key={opt.value}
                        onClick={() => onChange(opt.value)}
                        className={`flex-1 px-2 py-1.5 text-xs rounded-lg font-medium transition-colors cursor-pointer ${
                            value === opt.value
                                ? 'bg-purple-600 text-white'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                    >
                        {opt.label}
                    </button>
                ))}
            </div>
        </div>
    );
}
