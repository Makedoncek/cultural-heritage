import {useState} from 'react';
import {Link, NavLink} from 'react-router';
import {useAuth} from '../../context/AuthContext';

const linkClass = ({isActive}: { isActive: boolean }) =>
    isActive ? 'text-amber-700 font-semibold' : 'text-gray-700 hover:text-amber-700';

export default function Header() {
    const {user, isAuthenticated, loading, logout} = useAuth();
    const [menuOpen, setMenuOpen] = useState(false);

    return (
        <header className="bg-white border-b border-gray-200 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-16">
                <Link to="/" className="flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7 text-amber-600" viewBox="0 0 24 24"
                         fill="currentColor">
                        <path fillRule="evenodd"
                              d="M11.54 22.351l.07.04.028.016a.76.76 0 00.723 0l.028-.015.071-.041a16.975 16.975 0 001.144-.742 19.58 19.58 0 002.683-2.282c1.944-1.99 3.963-4.98 3.963-8.827a8.25 8.25 0 00-16.5 0c0 3.846 2.02 6.837 3.963 8.827a19.58 19.58 0 002.682 2.282 16.975 16.975 0 001.145.742zM12 13.5a3 3 0 100-6 3 3 0 000 6z"
                              clipRule="evenodd"/>
                    </svg>
                    <span className="text-amber-900 font-bold text-xl">CultureMap</span>
                </Link>

                {!loading && (
                    <>
                        <nav className="hidden md:flex items-center gap-4">
                            {isAuthenticated ? (
                                <>
                                    <NavLink to="/" end className={linkClass}>Карта</NavLink>
                                    <NavLink to="/my-objects" className={linkClass}>Мої об'єкти</NavLink>
                                    <NavLink to="/objects/add" className={linkClass}>Додати об'єкт</NavLink>
                                    <span className="text-amber-800 font-medium">{user?.username}</span>
                                    <button
                                        onClick={logout}
                                        className="bg-amber-600 text-white px-4 py-2 rounded-lg hover:bg-amber-700 transition-colors"
                                    >
                                        Вийти
                                    </button>
                                </>
                            ) : (
                                <>
                                    <Link to="/login" className="border border-amber-600 text-amber-700 px-4 py-2 rounded-lg hover:bg-amber-50 transition-colors">Увійти</Link>
                                    <Link to="/register"
                                          className="bg-amber-600 text-white px-4 py-2 rounded-lg hover:bg-amber-700 transition-colors">
                                        Реєстрація
                                    </Link>
                                </>
                            )}
                        </nav>

                        <button
                            onClick={() => setMenuOpen(!menuOpen)}
                            className="md:hidden p-2 text-gray-600 hover:text-amber-700"
                            aria-label="Меню"
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
                <nav className="md:hidden border-t border-gray-100 px-4 py-3 flex flex-col gap-3">
                    {isAuthenticated ? (
                        <>
                            <NavLink to="/" end className={linkClass}
                                     onClick={() => setMenuOpen(false)}>Карта</NavLink>
                            <NavLink to="/my-objects" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>Мої об'єкти</NavLink>
                            <NavLink to="/objects/add" className={linkClass}
                                     onClick={() => setMenuOpen(false)}>Додати об'єкт</NavLink>
                            <div className="border-t border-gray-100 pt-3 flex items-center justify-between">
                                <span className="text-amber-800 font-medium">{user?.username}</span>
                                <button
                                    onClick={() => {
                                        logout();
                                        setMenuOpen(false);
                                    }}
                                    className="bg-amber-600 text-white px-4 py-2 rounded-lg hover:bg-amber-700 transition-colors"
                                >
                                    Вийти
                                </button>
                            </div>
                        </>
                    ) : (
                        <>
                            <Link to="/login" className="border border-amber-600 text-amber-700 px-4 py-2 rounded-lg hover:bg-amber-50 transition-colors text-center"
                                  onClick={() => setMenuOpen(false)}>Увійти</Link>
                            <Link to="/register"
                                  className="bg-amber-600 text-white px-4 py-2 rounded-lg hover:bg-amber-700 transition-colors text-center"
                                  onClick={() => setMenuOpen(false)}>
                                Реєстрація
                            </Link>
                        </>
                    )}
                </nav>
            )}
        </header>
    );
}