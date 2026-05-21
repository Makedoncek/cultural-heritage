import {useTheme} from '../../context/ThemeContext';
import {useAuth} from '../../context/AuthContext';
import {preferenceService} from '../../services/preference.service';

export default function ThemeSwitcher() {
    const {theme, toggleTheme} = useTheme();
    const {isAuthenticated} = useAuth();
    const isDark = theme === 'dark';

    const handleClick = () => {
        const next = isDark ? 'light' : 'dark';
        toggleTheme();
        if (isAuthenticated) {
            preferenceService.update({theme: next}).catch(() => {});
        }
    };

    return (
        <button
            type="button"
            onClick={handleClick}
            aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
            title={isDark ? 'Світла тема' : 'Темна тема'}
            className="w-8 h-8 inline-flex items-center justify-center rounded-full border border-amber-200 bg-amber-50/80 text-amber-700 hover:bg-amber-100 dark:border-stone-600 dark:bg-stone-800 dark:text-amber-300 dark:hover:bg-stone-700 transition-colors cursor-pointer"
        >
            {isDark ? (
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="4"/>
                    <path strokeLinecap="round" d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
                </svg>
            ) : (
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
            )}
        </button>
    );
}
