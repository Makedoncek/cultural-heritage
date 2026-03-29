import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {useSearchParams, Link} from 'react-router';
import {authService} from '../services/auth.service';
import {AxiosError} from 'axios';
import UkraineMapBg from '../components/UkraineMapBg';

interface ResetForm {
    password: string;
    password2: string;
}

function ResetPasswordPage() {
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
                message: Array.isArray(errorMsg) ? errorMsg[0] : (errorMsg || 'Помилка скидання пароля.'),
            });
        }
    };

    const inputClass = (field: keyof ResetForm) =>
        `w-full border rounded-lg px-3 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400 transition-colors ${
            errors[field] ? 'border-red-400' : 'border-gray-200'
        }`;

    if (!uid || !token) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 px-4">
                <div className="w-full max-w-md">
                    <div className="relative flex flex-col items-center mb-6">
                        <UkraineMapBg/>
                        <div className="mt-2">
                            <h1 className="text-2xl font-bold text-amber-900 text-center">CultureMap</h1>
                            <p className="text-sm text-amber-700/70 mt-1 text-center">Культурна спадщина України</p>
                        </div>
                    </div>
                    <div className="bg-white/80 backdrop-blur rounded-2xl shadow-lg shadow-amber-900/5 border border-amber-100 p-8 text-center">
                        <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                        </svg>
                        <h2 className="text-xl font-semibold text-red-700 mb-3">Недійсне посилання</h2>
                        <Link to="/forgot-password" className="text-amber-700 font-medium hover:text-amber-800 hover:underline">
                            Запросити нове посилання
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

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
                        <p className="text-sm text-amber-700/70 mt-1 text-center">Культурна спадщина України</p>
                    </div>
                </div>
                <div className="bg-white/80 backdrop-blur rounded-2xl shadow-lg shadow-amber-900/5 border border-amber-100 p-8">
                    {success ? (
                        <div className="text-center">
                            <svg className="w-12 h-12 text-green-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                            </svg>
                            <h2 className="text-xl font-semibold text-green-700 mb-3">Пароль змінено!</h2>
                            <p className="text-gray-600 mb-4">Тепер ви можете увійти з новим паролем.</p>
                            <Link to="/login"
                                  className="inline-block bg-amber-600 text-white py-2.5 px-8 rounded-lg font-medium hover:bg-amber-700 transition-colors">
                                Увійти
                            </Link>
                        </div>
                    ) : (
                        <>
                            <h2 className="text-xl font-semibold text-gray-800 text-center mb-5">Новий пароль</h2>
                            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                                <div>
                                    <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                                        Пароль
                                    </label>
                                    <input
                                        id="password"
                                        type="password"
                                        autoComplete="new-password"
                                        className={inputClass('password')}
                                        {...register('password', {required: "Це поле обов'язкове"})}
                                    />
                                    <p className="text-gray-500 text-xs mt-1">Мінімум 8 символів, не лише цифри</p>
                                    {errors.password && <p className="text-red-600 text-sm mt-1">{errors.password.message}</p>}
                                </div>
                                <div>
                                    <label htmlFor="password2" className="block text-sm font-medium text-gray-700 mb-1">
                                        Підтвердження пароля
                                    </label>
                                    <input
                                        id="password2"
                                        type="password"
                                        autoComplete="new-password"
                                        className={inputClass('password2')}
                                        {...register('password2', {
                                            required: "Це поле обов'язкове",
                                            validate: (value) =>
                                                value === watch('password') || 'Паролі не збігаються',
                                        })}
                                    />
                                    {errors.password2 && <p className="text-red-600 text-sm mt-1">{errors.password2.message}</p>}
                                </div>

                                {errors.root && (
                                    <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                                        <p className="text-red-700 text-sm text-center">{errors.root.message}</p>
                                    </div>
                                )}

                                <button
                                    type="submit"
                                    disabled={isSubmitting}
                                    className="w-full bg-amber-600 text-white py-2.5 rounded-lg font-medium hover:bg-amber-700 disabled:opacity-50 transition-colors"
                                >
                                    {isSubmitting ? 'Збереження...' : 'Змінити пароль'}
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

