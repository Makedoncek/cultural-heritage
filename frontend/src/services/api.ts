import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // Якщо 401 і ще не пробували refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                const refreshToken = localStorage.getItem('refresh_token');
                if (!refreshToken) throw new Error('No refresh token');

                // Використовуємо чистий axios (не api instance) щоб уникнути цикл
                const {data} = await axios.post(
                    `${api.defaults.baseURL}/auth/refresh/`,
                    {refresh: refreshToken}
                );

                localStorage.setItem('access_token', data.access);

                if (data.refresh) {
                    localStorage.setItem('refresh_token', data.refresh);
                }

                originalRequest.headers.Authorization = `Bearer ${data.access}`;
                return api(originalRequest);
            } catch (refreshError) {
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');

                window.dispatchEvent(new Event('auth:logout'))
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);

export default api;