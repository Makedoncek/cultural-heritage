import {createContext, useContext, useState, useEffect, type ReactNode} from 'react';
import {authService} from '../services/auth.service';
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

const userFromPayload = (payload: { user_id: number; username?: string, is_staff?: boolean }): User => ({
    id: payload.user_id,
    username: payload.username || 'Користувач',
    is_staff: payload.is_staff ?? false,
});

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

    const checkAuth = () => {
        const token = localStorage.getItem('access_token');
        if (token) {
            try {
                const payload = parseJwtPayload(token);
                if (payload.exp * 1000 > Date.now()) {
                    setUser(userFromPayload(payload));
                } else {
                    clearAuth();
                }
            } catch {
                clearAuth();
            }
        }
        setLoading(false);
    };

    const login = async (credentials: LoginData) => {
        const tokens = await authService.login(credentials);

        localStorage.setItem('access_token', tokens.access);
        localStorage.setItem('refresh_token', tokens.refresh);

        const payload = parseJwtPayload(tokens.access);
        setUser(userFromPayload(payload));
    };

    const register = async (userData: RegisterData) => {
        const response = await authService.register(userData);

        localStorage.setItem('access_token', response.tokens.access);
        localStorage.setItem('refresh_token', response.tokens.refresh);

        const payload = parseJwtPayload(response.tokens.access);
        setUser(userFromPayload(payload));
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