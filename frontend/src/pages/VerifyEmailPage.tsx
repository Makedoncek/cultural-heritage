import {useEffect, useState} from 'react';
import {useSearchParams, Link} from 'react-router';
import {authService} from '../services/auth.service';
import {AxiosError} from 'axios';
import UkraineMapBg from '../components/UkraineMapBg';

function VerifyEmailPage() {
    const [searchParams] = useSearchParams();
    const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
    const [message, setMessage] = useState('');

    useEffect(() => {
        const token = searchParams.get('token');
        if (!token) {
            setStatus('error');
            setMessage('Токен не надано.');
            return;
        }

        authService.verifyEmail(token)
            .then(data => {
                setStatus('success');
                setMessage(data.message);
            })
            .catch((err: AxiosError<{ error: string }>) => {
                setStatus('error');
                setMessage(err.response?.data?.error || 'Помилка верифікації.');
            });
    }, [searchParams]);

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
                    {status === 'loading' && (
                        <p className="text-gray-600">Підтвердження пошти...</p>
                    )}
                    {status === 'success' && (
                        <>
                            <svg className="w-12 h-12 text-green-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                            </svg>
                            <h2 className="text-xl font-semibold text-green-700 mb-3">{message}</h2>
                            <Link to="/login"
                                  className="inline-block mt-2 bg-amber-600 text-white py-2.5 px-8 rounded-lg font-medium hover:bg-amber-700 transition-colors">
                                Увійти
                            </Link>
                        </>
                    )}
                    {status === 'error' && (
                        <>
                            <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                            </svg>
                            <h2 className="text-xl font-semibold text-red-700 mb-3">{message}</h2>
                            <Link to="/register"
                                  className="text-amber-700 font-medium hover:text-amber-800 hover:underline">
                                Спробувати знову
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

export default VerifyEmailPage;
