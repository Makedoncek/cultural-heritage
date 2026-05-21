import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {useSearchParams, Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import {authService} from '../services/auth.service';
import {AxiosError} from 'axios';
import UkraineMapBg from '../components/UkraineMapBg';

interface ResetForm {
    password: string;
    password2: string;
}

function ResetPasswordPage() {
    const {t} = useTranslation();
    const [searchParams] = useSearchParams();
    const uid = searchParams.get('uid') || '';
    const token = searchParams.get('token') || '';
    const [success, setSuccess] = useState(false);
    const {register, handleSubmit, watch, setError, formState: {errors, isSubmitting}} = useForm<ResetForm>();

    const onSubmit = async (data: ResetForm) => {
        try {
            await authService.confirmPasswordReset({uid, token, ...data});
            setSuccess(true);
        } catch (err) {
            const axiosError = err as AxiosError<{ error: string | string[] }>;
            const errorMsg = axiosError.response?.data?.error;
            setError('root', {
                message: Array.isArray(errorMsg) ? errorMsg[0] : (errorMsg || t('auth.resetErrorGeneric')),
            });
        }
    };

    const inputClass = (field: keyof ResetForm) =>
        `w-full border rounded-lg px-3 py-2.5 bg-white dark:bg-stone-800 text-gray-900 dark:text-stone-100 placeholder-gray-400 dark:placeholder-stone-500 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400 transition-colors ${
            errors[field] ? 'border-red-400' : 'border-gray-200 dark:border-stone-700'
        }`;

    if (!uid || !token) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 dark:from-stone-950 dark:via-stone-900 dark:to-stone-950 px-4">
                <div className="w-full max-w-md">
                    <div className="relative flex flex-col items-center mb-6">
                        <UkraineMapBg/>
                        <div className="mt-2">
                            <h1 className="text-2xl font-bold text-amber-900 dark:text-amber-300 text-center">CultureMap</h1>
                            <p className="text-sm text-amber-700/70 dark:text-amber-200/60 mt-1 text-center">{t('auth.tagline')}</p>
                        </div>
                    </div>
                    <div className="bg-white/80 dark:bg-stone-900/80 backdrop-blur rounded-2xl shadow-lg shadow-amber-900/5 border border-amber-100 dark:border-stone-700 p-8 text-center">
                        <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                        </svg>
                        <h2 className="text-xl font-semibold text-red-700 dark:text-red-400 mb-3">{t('auth.resetInvalidLink')}</h2>
                        <Link to="/forgot-password" className="text-amber-700 dark:text-amber-400 font-medium hover:text-amber-800 dark:hover:text-amber-300 hover:underline">
                            {t('auth.resetRequestNewLink')}
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 dark:from-stone-950 dark:via-stone-900 dark:to-stone-950 px-4">
            <div className="w-full max-w-md">
                <div className="relative flex flex-col items-center mb-6">
                    <UkraineMapBg/>
                    <div className="absolute top-2 left-[52%] -translate-x-1/2 inline-flex items-center justify-center w-16 h-16">
                        <svg className="w-10 h-10 text-amber-700 dark:text-amber-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"/>
                        </svg>
                    </div>
                    <div className="mt-2">
                        <h1 className="text-2xl font-bold text-amber-900 dark:text-amber-300 text-center">CultureMap</h1>
                        <p className="text-sm text-amber-700/70 dark:text-amber-200/60 mt-1 text-center">{t('auth.tagline')}</p>
                    </div>
                </div>
                <div className="bg-white/80 dark:bg-stone-900/80 backdrop-blur rounded-2xl shadow-lg shadow-amber-900/5 border border-amber-100 dark:border-stone-700 p-8">
                    {success ? (
                        <div className="text-center">
                            <svg className="w-12 h-12 text-green-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                            </svg>
                            <h2 className="text-xl font-semibold text-green-700 dark:text-green-400 mb-3">{t('auth.resetSuccessTitle')}</h2>
                            <p className="text-gray-600 dark:text-stone-300 mb-4">{t('auth.resetSuccessDesc')}</p>
                            <Link to="/login"
                                  className="inline-block bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 py-2.5 px-8 rounded-lg font-medium transition-colors">
                                {t('auth.loginNow')}
                            </Link>
                        </div>
                    ) : (
                        <>
                            <h2 className="text-xl font-semibold text-gray-800 dark:text-stone-100 text-center mb-5">{t('auth.resetTitle')}</h2>
                            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                                <div>
                                    <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                                        {t('auth.password')}
                                    </label>
                                    <input
                                        id="password"
                                        type="password"
                                        autoComplete="new-password"
                                        className={inputClass('password')}
                                        {...register('password', {required: t('auth.required')})}
                                    />
                                    <p className="text-gray-500 dark:text-stone-400 text-xs mt-1">{t('auth.passwordHint')}</p>
                                    {errors.password && <p className="text-red-600 dark:text-red-400 text-sm mt-1">{errors.password.message}</p>}
                                </div>
                                <div>
                                    <label htmlFor="password2" className="block text-sm font-medium text-gray-700 dark:text-stone-200 mb-1">
                                        {t('auth.passwordConfirm')}
                                    </label>
                                    <input
                                        id="password2"
                                        type="password"
                                        autoComplete="new-password"
                                        className={inputClass('password2')}
                                        {...register('password2', {
                                            required: t('auth.required'),
                                            validate: (value) =>
                                                value === watch('password') || t('auth.passwordMismatch'),
                                        })}
                                    />
                                    {errors.password2 && <p className="text-red-600 dark:text-red-400 text-sm mt-1">{errors.password2.message}</p>}
                                </div>

                                {errors.root && (
                                    <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
                                        <p className="text-red-700 dark:text-red-300 text-sm text-center">{errors.root.message}</p>
                                    </div>
                                )}

                                <button
                                    type="submit"
                                    disabled={isSubmitting}
                                    className="w-full bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-stone-900 py-2.5 rounded-lg font-medium disabled:opacity-50 transition-colors cursor-pointer"
                                >
                                    {isSubmitting ? t('auth.resetSubmitting') : t('auth.resetSubmit')}
                                </button>
                            </form>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ResetPasswordPage;
