import {useState} from 'react';
import {Link, NavLink} from 'react-router';
import {useTranslation} from 'react-i18next';
import {useAuth} from '../../context/AuthContext';
import LanguageSwitcher from './LanguageSwitcher';
import ThemeSwitcher from './ThemeSwitcher';

const linkClass = ({isActive}: { isActive: boolean }) =>
    isActive
        ? 'text-amber-700 dark:text-amber-400 font-semibold'
        : 'text-gray-700 dark:text-stone-300 hover:text-amber-700 dark:hover:text-amber-400';

const ADMIN_URL = (import.meta.env.VITE_API_URL as string || 'http://localhost:8000/api').replace(/\/api\/?$/, '/admin/');

export default function Header() {
    const {user, isAuthenticated, loading, logout} = useAuth();
    const {t} = useTranslation();
    const [menuOpen, setMenuOpen] = useState(false);

    return (
        <header className="bg-white dark:bg-stone-900 border-b border-gray-200 dark:border-stone-700 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-16">
                <Link to="/" className="flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7 text-amber-600 dark:text-amber-400" viewBox="0 0 24 24"
                         fill="currentColor">
                        <path fillRule="evenodd"
                              d="M11.54 22.351l.07.04.028.016a.76.76 0 00.723 0l.028-.015.071-.041a16.975 16.975 0 001.144-.742 19.58 19.58 0 002.683-2.282c1.944-1.99 3.963-4.98 3.963-8.827a8.25 8.25 0 00-16.5 0c0 3.846 2.02 6.837 3.963 8.827a19.58 19.58 0 002.682 2.282 16.975 16.975 0 001.145.742zM12 13.5a3 3 0 100-6 3 3 0 000 6z"
                              clipRule="evenodd"/>
                    </svg>
                    <span className="text-amber-900 dark:text-amber-300 font-bold text-xl">CultureMap</span>
                </Link>

                {!loading && (
                    <>
                        <nav className="hidden md:flex items-center gap-4">
                            {isAuthenticated ? (
                                <>
                                    <NavLink to="/" end className={linkClass}>{t('nav.map')}</NavLink>
                                    <NavLink to="/popular" className={linkClass}>{t('nav.popular')}</NavLink>
                                    <NavLink to="/routes" className={linkClass}>🗺 Маршрути</NavLink>
                                    <NavLink to="/my-objects" className={linkClass}>{t('nav.myObjects')}</NavLink>
                                    <NavLink to="/my-contributions" className={linkClass}>{t('nav.myContributions')}</NavLink>
                                    <NavLink to="/favorites" className={linkClass}>{t('nav.favorites')}</NavLink>
                                    <NavLink to="/favorite-authors" className={linkClass}>{t('nav.subscriptions')}</NavLink>
                                    <NavLink to="/objects/add" className={linkClass}>{t('nav.addObject')}</NavLink>
                                    {user?.is_staff && (
                                        <a
                                            href={ADMIN_URL}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-purple-700 dark:text-purple-400 hover:text-purple-900 dark:hover:text-purple-300 font-medium"
                                            title="Django admin"
                                        >
                                            🛠 {t('nav.admin')}
                                        </a>
                                    )}
                                    <Link to={`/authors/${user?.username}`} className="text-amber-800 dark:text-amber-300 font-medium hover:text-amber-600 dark:hover:text-amber-200">{user?.username}</Link>
                                    <ThemeSwitcher/>
                                    <LanguageSwitcher/>
                                    <button
                                        onClick={logout}
                                        className="bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 px-4 py-2 rounded-lg transition-colors cursor-pointer"
                                    >
                                        {t('nav.logout')}
                                    </button>
                                </>
                            ) : (
                                <>
                                    <NavLink to="/popular" className={linkClass}>{t('nav.popular')}</NavLink>
                                    <NavLink to="/routes" className={linkClass}>🗺 Маршрути</NavLink>
                                    <ThemeSwitcher/>
                                    <LanguageSwitcher/>
                                    <Link to="/login" className="border border-amber-600 dark:border-amber-500 text-amber-700 dark:text-amber-300 px-4 py-2 rounded-lg hover:bg-amber-50 dark:hover:bg-stone-800 transition-colors">{t('nav.login')}</Link>
                                    <Link to="/register"
                                          className="bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 px-4 py-2 rounded-lg transition-colors">
                                        {t('nav.register')}
                                    </Link>
                                </>
                            )}
                        </nav>

                        <button
                            onClick={() => setMenuOpen(!menuOpen)}
                            className="md:hidden p-2 text-gray-600 dark:text-stone-300 hover:text-amber-700 dark:hover:text-amber-400"
                            aria-label={t('nav.menu')}
                        >
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"
                                 strokeWidth={2}>
                                {menuOpen ? (
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
                                ) : (
                                    <path strokeLinecap="round" strokeLinejoin="round"
                                          d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"/>
                                )}
                            </svg>
                        </button>
                    </>
                )}
            </div>

            {!loading && menuOpen && (
                <nav className="md:hidden border-t border-gray-100 dark:border-stone-700 px-4 py-3 flex flex-col gap-3 bg-white dark:bg-stone-900">
                    {isAuthenticated ? (
                        <>
                            <NavLink to="/" end className={linkClass}
                                     onClick={() => setMenuOpen(false)}>{t('nav.map')}</NavLink>
                            <NavLink to="/popular" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>{t('nav.popular')}</NavLink>
                            <NavLink to="/routes" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>🗺 {t('nav.routes')}</NavLink>
                            <NavLink to="/my-objects" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>{t('nav.myObjects')}</NavLink>
                            <NavLink to="/my-contributions" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>{t('nav.myContributions')}</NavLink>
                            <NavLink to="/favorites" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>{t('nav.favorites')}</NavLink>
                            <NavLink to="/favorite-authors" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>{t('nav.subscriptions')}</NavLink>
                            <NavLink to="/objects/add" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>{t('nav.addObject')}</NavLink>
                            {user?.is_staff && (
                                <a
                                    href={ADMIN_URL}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-purple-700 dark:text-purple-400 hover:text-purple-900 dark:hover:text-purple-300 font-medium"
                                    onClick={() => setMenuOpen(false)}
                                >
                                    🛠 {t('nav.admin')}
                                </a>
                            )}
                            <div className="border-t border-gray-100 dark:border-stone-700 pt-3 flex items-center justify-between gap-2">
                                <Link to={`/authors/${user?.username}`} className="text-amber-800 dark:text-amber-300 font-medium hover:text-amber-600 dark:hover:text-amber-200 flex-1" onClick={() => setMenuOpen(false)}>{user?.username}</Link>
                                <ThemeSwitcher/>
                                <LanguageSwitcher/>
                                <button
                                    onClick={() => {
                                        logout();
                                        setMenuOpen(false);
                                    }}
                                    className="bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 px-4 py-2 rounded-lg transition-colors cursor-pointer"
                                >
                                    {t('nav.logout')}
                                </button>
                            </div>
                        </>
                    ) : (
                        <>
                            <NavLink to="/popular" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>{t('nav.popular')}</NavLink>
                            <NavLink to="/routes" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>🗺 {t('nav.routes')}</NavLink>
                            <div className="flex items-center gap-2">
                                <ThemeSwitcher/>
                                <LanguageSwitcher/>
                            </div>
                            <Link to="/login" className="border border-amber-600 dark:border-amber-500 text-amber-700 dark:text-amber-300 px-4 py-2 rounded-lg hover:bg-amber-50 dark:hover:bg-stone-800 transition-colors text-center"
                                  onClick={() => setMenuOpen(false)}>{t('nav.login')}</Link>
                            <Link to="/register"
                                  className="bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 px-4 py-2 rounded-lg transition-colors text-center"
                                  onClick={() => setMenuOpen(false)}>
                                {t('nav.register')}
                            </Link>
                        </>
                    )}
                </nav>
            )}
        </header>
    );
}
