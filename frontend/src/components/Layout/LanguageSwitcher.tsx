import {useTranslation} from 'react-i18next';
import {useAuth} from '../../context/AuthContext';
import {preferenceService, type Language} from '../../services/preference.service';

const LANGUAGES = [
    {code: 'uk', label: 'UA'},
    {code: 'en', label: 'EN'},
] as const;

export default function LanguageSwitcher() {
    const {i18n, t} = useTranslation();
    const {isAuthenticated} = useAuth();
    const current = i18n.resolvedLanguage || 'uk';

    const select = (code: string) => {
        if (code === current) return;
        void i18n.changeLanguage(code);
        document.documentElement.lang = code;
        if (isAuthenticated) {
            preferenceService.update(code as Language).catch(() => {
                /* server sync is best-effort — UI is already updated */
            });
        }
    };

    return (
        <div
            className="inline-flex items-center bg-amber-50/80 border border-amber-200 rounded-full p-0.5 shadow-sm"
            role="group"
            aria-label={t('lang.ukFull') + ' / ' + t('lang.enFull')}
        >
            {LANGUAGES.map(({code, label}) => {
                const active = current === code;
                return (
                    <button
                        key={code}
                        type="button"
                        onClick={() => select(code)}
                        aria-pressed={active}
                        title={code === 'uk' ? t('lang.ukFull') : t('lang.enFull')}
                        className={`
                            px-3 py-1 rounded-full text-xs font-semibold tracking-wide
                            transition-all duration-200 cursor-pointer
                            ${active
                                ? 'bg-amber-600 text-white shadow-sm'
                                : 'text-amber-700/70 hover:text-amber-800 hover:bg-amber-100'}
                        `}
                    >
                        {label}
                    </button>
                );
            })}
        </div>
    );
}
