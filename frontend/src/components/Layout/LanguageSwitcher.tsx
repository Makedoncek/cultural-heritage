import {useTranslation} from 'react-i18next';

export default function LanguageSwitcher() {
    const {i18n, t} = useTranslation();
    const current = i18n.resolvedLanguage || 'uk';

    const toggle = () => {
        const next = current === 'uk' ? 'en' : 'uk';
        void i18n.changeLanguage(next);
        document.documentElement.lang = next;
    };

    return (
        <button
            type="button"
            onClick={toggle}
            className="text-xs font-semibold px-2 py-1 border border-amber-300 rounded text-amber-700 hover:bg-amber-50 cursor-pointer"
            title={current === 'uk' ? t('lang.enFull') : t('lang.ukFull')}
            aria-label="Switch language"
        >
            {current === 'uk' ? t('lang.en') : t('lang.uk')}
        </button>
    );
}
