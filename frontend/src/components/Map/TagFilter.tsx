import type {Tag} from '../../types';

interface TagFilterProps {
    tags: Tag[];
    selectedTags: number[];
    onTagToggle: (tagId: number) => void;
    onClear: () => void;
}

export default function TagFilter({tags, selectedTags, onTagToggle, onClear}: TagFilterProps) {
    return (
        <div className="flex flex-col gap-1">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">Фільтр за тегами</h3>

            {tags.map(tag => (
                <label
                    key={tag.id}
                    className="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-amber-50 transition-colors"
                >
                    <input
                        type="checkbox"
                        checked={selectedTags.includes(tag.id)}
                        onChange={() => onTagToggle(tag.id)}
                        className="w-4 h-4 accent-amber-500 cursor-pointer"
                    />
                    <span className="text-base">{tag.icon}</span>
                    <span className="text-sm text-gray-700">{tag.name}</span>
                </label>
            ))}

            {selectedTags.length > 0 && (
                <button
                    onClick={onClear}
                    className="mt-2 text-sm text-amber-600 hover:text-amber-800 cursor-pointer text-left"
                >
                    Скинути фільтри
                </button>
            )}
        </div>
    );
}