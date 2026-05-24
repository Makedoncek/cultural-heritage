import {useTranslation} from 'react-i18next';

export type ContentLanguage = 'uk' | 'en' | 'pl' | 'de';

const LANG_TO_ISO: Record<ContentLanguage, string> = {
    uk: 'ua',
    en: 'gb',
    pl: 'pl',
    de: 'de',
};

const LANG_LABEL: Record<ContentLanguage, string> = {
    uk: 'UA',
    en: 'EN',
    pl: 'PL',
    de: 'DE',
};

interface Props {
    available: ContentLanguage[];
    selected: ContentLanguage;
    onSelect: (lang: ContentLanguage) => void;
    /** Show a "suggest a translation" action button at the end. */
    onSuggest?: () => void;
}

export default function ContentLanguageSelector({available, selected, onSelect, onSuggest}: Props) {
    const {t} = useTranslation();

    // Nothing meaningful to show unless there's a choice or a way to contribute.
    if (available.length <= 1 && !onSuggest) return null;

    return (
        <div className="flex items-center gap-2 mb-3 flex-wrap">
            <span className="text-xs text-gray-500 dark:text-stone-400 mr-1">
                {t('translations.contentLanguage')}:
            </span>
            {available.map(l => (
                <button
                    key={l}
                    type="button"
                    onClick={() => onSelect(l)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1 text-sm font-medium rounded-full border cursor-pointer transition-colors ${
                        selected === l
                            ? 'bg-amber-100 dark:bg-amber-900/40 border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-300'
                            : 'border-gray-200 dark:border-stone-700 text-gray-600 dark:text-stone-300 hover:border-gray-400'
                    }`}
                >
                    <img
                        src={`https://flagcdn.com/20x15/${LANG_TO_ISO[l]}.png`}
                        alt=""
                        width={20}
                        height={15}
                        className="rounded-[2px]"
                    />
                    {LANG_LABEL[l]}
                </button>
            ))}
            {onSuggest && (
                <button
                    type="button"
                    onClick={onSuggest}
                    className="inline-flex items-center gap-1 px-3 py-1 text-sm rounded-full border border-dashed border-gray-300 dark:border-stone-600 text-gray-500 dark:text-stone-400 hover:border-amber-400 hover:text-amber-700 dark:hover:text-amber-300 cursor-pointer"
                    title={t('translations.suggest')}
                >
                    ＋ {t('translations.suggest')}
                </button>
            )}
        </div>
    );
}
