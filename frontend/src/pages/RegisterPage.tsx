import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {Link, Navigate} from 'react-router';
import {useAuth} from '../context/AuthContext';
import type {RegisterData} from '../types';
import {AxiosError} from 'axios';
import UkraineMapBg from '../components/UkraineMapBg';

type ServerErrors = Record<string, string[]>;

function RegisterPage() {
    const {register: registerUser, isAuthenticated} = useAuth();
    const [success, setSuccess] = useState(false);
    const [registeredEmail, setRegisteredEmail] = useState('');
    const {
        register,
        handleSubmit,
        setError,
        watch,
        formState: {errors, isSubmitting},
    } = useForm<RegisterData>();

    if (isAuthenticated) return <Navigate to="/"/>;

    const onSubmit = async (data: RegisterData) => {
        try {
            await registerUser(data);
            setRegisteredEmail(data.email);
            setSuccess(true);
        } catch (err) {
            const axiosError = err as AxiosError<ServerErrors>;
            if (axiosError.response?.status === 400 && axiosError.response.data) {
                const serverErrors = axiosError.response.data;
                for (const [field, messages] of Object.entries(serverErrors)) {
                    if (['username', 'email', 'password', 'password2'].includes(field)) {
                        setError(field as keyof RegisterData, {message: messages[0]});
                    }
                }
                if (serverErrors.non_field_errors) {
                    setError('root', {message: serverErrors.non_field_errors[0]});
                }
            } else {
                setError('root', {message: 'Не вдалося з\'єднатися з сервером'});
            }
        }
    };

    const inputClass = (field: keyof RegisterData) =>
        `w-full border rounded-lg px-3 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400 transition-colors ${
            errors[field] ? 'border-red-400' : 'border-gray-200'
        }`;

    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 px-4">
                <div className="w-full max-w-md">
                    <div className="relative flex flex-col items-center mb-6">
                        <UkraineMapBg/>
                        <div className="absolute top-2 left-[52%] -translate-x-1/2 inline-flex items-center justify-center w-16 h-16">
                            <svg className="w-10 h-10 text-amber-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"/>
                            </svg>
                        </div>
                        <div className="mt-2">
                            <h1 className="text-2xl font-bold text-amber-900 text-center">CultureMap</h1>
                            <p className="text-sm text-amber-700/70 mt-1 text-center">Культурна спадщина України</p>
                        </div>
                    </div>
                    <div className="bg-white/80 backdrop-blur rounded-2xl shadow-lg shadow-amber-900/5 border border-amber-100 p-8 text-center">
                        <h2 className="text-xl font-semibold text-gray-800 mb-3">Перевірте вашу пошту</h2>
                        <p className="text-gray-600 mb-4">
                            Ми надіслали лист на <strong>{registeredEmail}</strong>.
                            Натисніть на посилання в листі, щоб підтвердити акаунт.
                        </p>
                        <p className="text-sm text-gray-500 mb-6">
                            Не отримали листа? Перевірте папку «Спам».
                        </p>
                        <Link to="/login" className="text-amber-700 font-medium hover:text-amber-800 hover:underline">
                            Перейти до входу
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div
            className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 px-4">
            <div className="w-full max-w-md">
                <div className="relative flex flex-col items-center mb-6">
                    <UkraineMapBg/>
                    <div
                        className="absolute top-2 left-[52%] -translate-x-1/2 inline-flex items-center justify-center w-16 h-16">
                        <svg className="w-10 h-10 text-amber-700" fill="none" viewBox="0 0 24 24" stroke="currentColor"
                             strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round"
                                  d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/>
                            <path strokeLinecap="round" strokeLinejoin="round"
                                  d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z"/>
                        </svg>
                    </div>
                    <div className="mt-2">
                        <h1 className="text-2xl font-bold text-amber-900 text-center">CultureMap</h1>
                        <p className="text-sm text-amber-700/70 mt-1 text-center">Культурна спадщина України</p>
                    </div>
                </div>

                <div
                    className="bg-white/80 backdrop-blur rounded-2xl shadow-lg shadow-amber-900/5 border border-amber-100 p-8">
                    <h2 className="text-xl font-semibold text-gray-800 text-center mb-5">Реєстрація</h2>

                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                                Ім'я користувача
                            </label>
                            <input
                                id="username"
                                type="text"
                                autoComplete="username"
                                className={inputClass('username')}
                                {...register('username', {required: 'Це поле обов\'язкове'})}
                            />
                            {errors.username && (
                                <p className="text-red-600 text-sm mt-1">{errors.username.message}</p>
                            )}
                        </div>

                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                                Електронна пошта
                            </label>
                            <input
                                id="email"
                                type="email"
                                autoComplete="email"
                                className={inputClass('email')}
                                {...register('email', {required: 'Це поле обов\'язкове'})}
                            />
                            {errors.email && (
                                <p className="text-red-600 text-sm mt-1">{errors.email.message}</p>
                            )}
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                                Пароль
                            </label>
                            <input
                                id="password"
                                type="password"
                                autoComplete="new-password"
                                className={inputClass('password')}
                                {...register('password', {required: 'Це поле обов\'язкове'})}
                            />
                            <p className="text-gray-500 text-xs mt-1">Мінімум 8 символів, не лише цифри</p>
                            {errors.password && (
                                <p className="text-red-600 text-sm mt-1">{errors.password.message}</p>
                            )}
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
                                    required: 'Це поле обов\'язкове',
                                    validate: (value) =>
                                        value === watch('password') || 'Паролі не збігаються',
                                })}
                            />
                            {errors.password2 && (
                                <p className="text-red-600 text-sm mt-1">{errors.password2.message}</p>
                            )}
                        </div>

                        {errors.root && (
                            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                                <p className="text-red-700 text-sm text-center">{errors.root.message}</p>
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full bg-amber-600 text-white py-2.5 rounded-lg font-medium hover:bg-amber-700 active:bg-amber-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {isSubmitting ? 'Реєстрація...' : 'Зареєструватися'}
                        </button>
                    </form>

                    <div className="mt-5 pt-4 border-t border-gray-100">
                        <p className="text-center text-sm text-gray-600">
                            Вже є акаунт?{' '}
                            <Link to="/login"
                                  className="text-amber-700 font-medium hover:text-amber-800 hover:underline">
                                Увійти
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default RegisterPage;
