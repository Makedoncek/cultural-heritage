import {useForm} from 'react-hook-form';
import {Link, Navigate, useNavigate, useLocation} from 'react-router';
import {useTranslation} from 'react-i18next';
import {useAuth} from '../context/AuthContext';
import type {LoginData} from '../types';
import {AxiosError} from 'axios';
import UkraineMapBg from '../components/UkraineMapBg';

function LoginPage() {
    const {login, isAuthenticated} = useAuth();
    const {t} = useTranslation();
    const navigate = useNavigate();
    const location = useLocation();
    const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';
    const {
        register,
        handleSubmit,
        setError,
        formState: {errors, isSubmitting},
    } = useForm<LoginData>();

    if (isAuthenticated) return <Navigate to={from} replace/>;

    const onSubmit = async (data: LoginData) => {
        try {
            await login(data);
            navigate(from, {replace: true});
        } catch (err) {
            const axiosError = err as AxiosError;
            if (axiosError.response?.status === 401) {
                setError('root', {message: t('auth.invalidCredentials')});
            } else {
                setError('root', {message: t('auth.connectionError')});
            }
        }
    };

    return (
        <div
            className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 dark:from-stone-950 dark:via-stone-900 dark:to-stone-950 px-4">
            <div className="w-full max-w-md">
                <div className="relative flex flex-col items-center mb-6">
                    <UkraineMapBg/>
                    <div
                        className="absolute top-2 left-[52%] -translate-x-1/2 inline-flex items-center justify-center w-16 h-16">
                        <svg className="w-10 h-10 text-amber-700 dark:text-amber-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"
                             strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round"
                                  d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/>
                            <path strokeLinecap="round" strokeLinejoin="round"
                                  d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z"/>
                        </svg>
                    </div>
                    <div className="mt-2">
                        <h1 className="text-2xl font-bold text-amber-900 dark:text-amber-300 text-center">CultureMap</h1>
                        <p className="text-sm text-amber-700/70 dark:text-amber-200/60 mt-1 text-center">{t('auth.tagline')}</p>
                    </div>
                </div>


                <div
                    className="bg-white/80 dark:bg-stone-900/80 backdrop-blur rounded-2xl shadow-lg shadow-amber-900/5 border border-amber-100 dark:border-stone-700 p-8">
                    <h2 className="text-xl font-semibold text-gray-800 dark:text-stone-100 text-center mb-5">{t('auth.loginTitle')}</h2>

                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                                {t('auth.usernameOrEmail')}
                            </label>
                            <input
                                id="username"
                                type="text"
                                autoComplete="username"
                                placeholder={t('auth.loginPlaceholder')}
                                className={`w-full border rounded-lg px-3 py-2.5 bg-white dark:bg-stone-800 text-gray-900 dark:text-stone-100 placeholder-gray-400 dark:placeholder-stone-500 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400 transition-colors ${
                                    errors.username ? 'border-red-400' : 'border-gray-200 dark:border-stone-700'
                                }`}
                                {...register('username', {required: t('auth.required')})}
                            />
                            {errors.username && (
                                <p className="text-red-600 dark:text-red-400 text-sm mt-1">{errors.username.message}</p>
                            )}
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                                {t('auth.password')}
                            </label>
                            <input
                                id="password"
                                type="password"
                                autoComplete="current-password"
                                className={`w-full border rounded-lg px-3 py-2.5 bg-white dark:bg-stone-800 text-gray-900 dark:text-stone-100 placeholder-gray-400 dark:placeholder-stone-500 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400 transition-colors ${
                                    errors.password ? 'border-red-400' : 'border-gray-200 dark:border-stone-700'
                                }`}
                                {...register('password', {required: t('auth.required')})}
                            />
                            {errors.password && (
                                <p className="text-red-600 dark:text-red-400 text-sm mt-1">{errors.password.message}</p>
                            )}
                            <div className="flex justify-end">
                                <Link to="/forgot-password" className="text-sm text-amber-700 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 hover:underline">
                                    {t('auth.forgotPassword')}
                                </Link>
                            </div>
                        </div>

                        {errors.root && (
                            <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
                                <p className="text-red-700 dark:text-red-300 text-sm text-center">{errors.root.message}</p>
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full bg-amber-600 hover:bg-amber-700 active:bg-amber-800 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 py-2.5 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
                        >
                            {isSubmitting ? t('auth.submittingLogin') : t('auth.submitLogin')}
                        </button>
                    </form>

                    <div className="mt-5 pt-4 border-t border-gray-100 dark:border-stone-700">
                        <p className="text-center text-sm text-gray-600 dark:text-stone-300">
                            {t('auth.noAccount')}{' '}
                            <Link to="/register"
                                  className="text-amber-700 dark:text-amber-400 font-medium hover:text-amber-800 dark:hover:text-amber-300 hover:underline">
                                {t('auth.registerNow')}
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default LoginPage;
