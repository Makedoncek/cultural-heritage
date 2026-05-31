import {createContext, useContext, useEffect, useState, type ReactNode} from 'react';

export type Theme = 'light' | 'dark';

interface ThemeContextType {
    theme: Theme;
    toggleTheme: () => void;
    setTheme: (t: Theme) => void;
}

const STORAGE_KEY = 'culturemap_theme';

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const readInitial = (): Theme => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
    return globalThis.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

const applyToDocument = (theme: Theme) => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.documentElement.style.colorScheme = theme;
};

export const ThemeProvider = ({children}: {children: ReactNode}) => {
    const [theme, setThemeState] = useState<Theme>(readInitial);

    useEffect(() => {
        applyToDocument(theme);
        localStorage.setItem(STORAGE_KEY, theme);
    }, [theme]);

    useEffect(() => {
        const handler = (e: Event) => {
            const next = (e as CustomEvent<Theme>).detail;
            if (next === 'light' || next === 'dark') setThemeState(next);
        };
        globalThis.addEventListener('theme:apply', handler);
        return () => globalThis.removeEventListener('theme:apply', handler);
    }, []);

    const setTheme = (t: Theme) => setThemeState(t);
    const toggleTheme = () => setThemeState(prev => (prev === 'dark' ? 'light' : 'dark'));

    return (
        <ThemeContext.Provider value={{theme, toggleTheme, setTheme}}>
            {children}
        </ThemeContext.Provider>
    );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useTheme = (): ThemeContextType => {
    const ctx = useContext(ThemeContext);
    if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
    return ctx;
};
