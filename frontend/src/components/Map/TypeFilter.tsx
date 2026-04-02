interface TypeFilterProps {
    value: string;
    onChange: (value: string) => void;
}

const options = [
    {value: 'all', label: 'Усі'},
    {value: 'permanent', label: "Пам'ятки"},
    {value: 'event', label: 'Події'},
];

export default function TypeFilter({value, onChange}: TypeFilterProps) {
    return (
        <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Тип об'єкта</h3>
            <div className="flex gap-1">
                {options.map(opt => (
                    <button
                        key={opt.value}
                        onClick={() => onChange(opt.value)}
                        className={`flex-1 px-2 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                            value === opt.value
                                ? 'bg-amber-600 text-white'
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
