import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {Link} from 'react-router';
import {useTranslation} from 'react-i18next';
import {authService} from '../services/auth.service';
import UkraineMapBg from '../components/UkraineMapBg';

interface ForgotForm {
    email: string;
}

function ForgotPasswordPage() {
    const {t} = useTranslation();
    const [sent, setSent] = useState(false);
    const {register, handleSubmit, formState: {errors, isSubmitting}} = useForm<ForgotForm>();

    const onSubmit = async (data: ForgotForm) => {
        await authService.requestPasswordReset(data);
        setSent(true);
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 px-4">
            <div className="w-full max-w-md">
                <div className="relative flex flex-col items-center mb-6">
                    <UkraineMapBg/>
                    <div className="absolute top-2 left-[52%] -translate-x-1/2 inline-flex items-center justify-center w-16 h-16">
                        <svg className="w-10 h-10 text-amber-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"/>
                        </svg>
                    </div>
                    <div className="mt-2">
                        <h1 className="text-2xl font-bold text-amber-900 text-center">CultureMap</h1>
                        <p className="text-sm text-amber-700/70 mt-1 text-center">{t('auth.tagline')}</p>
                    </div>
                </div>
                <div className="bg-white/80 backdrop-blur rounded-2xl shadow-lg shadow-amber-900/5 border border-amber-100 p-8">
                    {sent ? (
                        <div className="text-center">
                            <svg className="w-12 h-12 text-amber-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"/>
                            </svg>
                            <h2 className="text-xl font-semibold text-gray-800 mb-3">{t('auth.forgotCheckEmailTitle')}</h2>
                            <p className="text-gray-600 mb-6">{t('auth.forgotCheckEmailDesc')}</p>
                            <Link to="/login" className="text-amber-700 font-medium hover:text-amber-800 hover:underline">
                                {t('auth.backToLogin')}
                            </Link>
                        </div>
                    ) : (
                        <>
                            <h2 className="text-xl font-semibold text-gray-800 text-center mb-5">{t('auth.forgotTitle')}</h2>
                            <p className="text-gray-600 text-sm text-center mb-4">{t('auth.forgotDesc')}</p>
                            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                                <div>
                                    <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                                        {t('auth.email')}
                                    </label>
                                    <input
                                        id="email"
                                        type="email"
                                        autoComplete="email"
                                        className={`w-full border rounded-lg px-3 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400 transition-colors ${errors.email ? 'border-red-400' : 'border-gray-200'}`}
                                        {...register('email', {required: t('auth.required')})}
                                    />
                                    {errors.email && <p className="text-red-600 text-sm mt-1">{errors.email.message}</p>}
                                </div>
                                <button
                                    type="submit"
                                    disabled={isSubmitting}
                                    className="w-full bg-amber-600 text-white py-2.5 rounded-lg font-medium hover:bg-amber-700 disabled:opacity-50 transition-colors cursor-pointer"
                                >
                                    {isSubmitting ? t('auth.forgotSubmitting') : t('auth.forgotSubmit')}
                                </button>
                            </form>
                            <div className="mt-5 pt-4 border-t border-gray-100">
                                <p className="text-center text-sm text-gray-600">
                                    {t('auth.rememberedPassword')}{' '}
                                    <Link to="/login" className="text-amber-700 font-medium hover:underline">{t('auth.loginNow')}</Link>
                                </p>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ForgotPasswordPage;
