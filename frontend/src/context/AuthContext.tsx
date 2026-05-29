import {createContext, useContext, useState, useEffect, type ReactNode} from 'react';
import i18n from '../i18n';
import {authService} from '../services/auth.service';
import {preferenceService} from '../services/preference.service';
import type {User, LoginData, RegisterData} from '../types';

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    loading: boolean;
    login: (credentials: LoginData) => Promise<void>;
    register: (data: RegisterData) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const parseJwtPayload = (token: string) => JSON.parse(atob(token.split('.')[1]));

// Tokens ultimately come from the network, so validate their shape (three base64url
// segments) before persisting — never write malformed/poisoned values to browser storage.
const isJwtFormat = (value: unknown): value is string =>
    typeof value === 'string' && /^[\w-]+\.[\w-]+\.[\w-]+$/.test(value);

const userFromPayload = (payload: { user_id: number; username?: string, is_staff?: boolean }): User => ({
    id: payload.user_id,
    username: payload.username || 'Користувач',
    is_staff: payload.is_staff ?? false,
});

// Pull server-stored preferences and apply them locally.
// Used on login (push wins for theme/lang user just picked) and on app boot if already logged in.
const syncPreferencesFromServer = async (pushLocal: boolean) => {
    try {
        if (pushLocal) {
            // User has an explicit local choice — push it to server so it persists across devices.
            const uiLang = i18n.resolvedLanguage === 'en' ? 'en' : 'uk';
            const uiTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
            await preferenceService.update({language: uiLang, theme: uiTheme});
            return;
        }
        const pref = await preferenceService.get();
        if (pref.language && pref.language !== i18n.resolvedLanguage) {
            await i18n.changeLanguage(pref.language);
            document.documentElement.lang = pref.language;
        }
        if (pref.theme) {
            window.dispatchEvent(new CustomEvent('theme:apply', {detail: pref.theme}));
        }
    } catch {
        // Best-effort sync — silent on failure (e.g. legacy user without preference row).
    }
};

export const AuthProvider = ({children}: { children: ReactNode }) => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    const isAuthenticated = !!user;

    useEffect(() => {
        checkAuth();

        const handleForceLogout = () => clearAuth();
        window.addEventListener('auth:logout', handleForceLogout);

        return () => window.removeEventListener('auth:logout', handleForceLogout);
    }, []);

    const checkAuth = async () => {
        const token = localStorage.getItem('access_token');
        if (token) {
            try {
                const payload = parseJwtPayload(token);
                if (payload.exp * 1000 > Date.now()) {
                    setUser(userFromPayload(payload));
                    // Returning user — server is source of truth for preferences.
                    void syncPreferencesFromServer(false);
                    setLoading(false);
                    return;
                }
            } catch {
                // Malformed token — fall through and try refresh as a recovery path.
            }
        }
        // Access token missing or expired — try refresh before bouncing the user.
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
            try {
                const tokens = await authService.refresh(refreshToken);
                if (!isJwtFormat(tokens.access)) {
                    throw new Error('Malformed access token');
                }
                localStorage.setItem('access_token', tokens.access);
                if (isJwtFormat(tokens.refresh)) {
                    localStorage.setItem('refresh_token', tokens.refresh);
                }
                const payload = parseJwtPayload(tokens.access);
                setUser(userFromPayload(payload));
                void syncPreferencesFromServer(false);
            } catch {
                clearAuth();
            }
        } else {
            clearAuth();
        }
        setLoading(false);
    };

    const login = async (credentials: LoginData) => {
        const tokens = await authService.login(credentials);

        if (!isJwtFormat(tokens.access)) {
            throw new Error('Malformed access token');
        }
        localStorage.setItem('access_token', tokens.access);
        if (isJwtFormat(tokens.refresh)) {
            localStorage.setItem('refresh_token', tokens.refresh);
        }

        const payload = parseJwtPayload(tokens.access);
        setUser(userFromPayload(payload));

        // Fresh login: push the currently-selected UI prefs so they persist server-side
        // (this is what most users expect — "I picked dark, now keep it on other devices").
        void syncPreferencesFromServer(true);
    };

    const register = async (userData: RegisterData) => {
        await authService.register(userData);
    };

    const logout = () => {
        clearAuth();
    };

    const clearAuth = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{user, isAuthenticated, loading, login, register, logout}}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};
