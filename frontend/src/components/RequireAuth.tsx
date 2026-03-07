import {Navigate, Outlet, useLocation} from 'react-router';
import {useAuth} from '../context/AuthContext';

export default function RequireAuth() {
    const {isAuthenticated, loading} = useAuth();
    const location = useLocation();

    if (loading) return null;

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{from: location}} replace/>;
    }

    return <Outlet/>;
}