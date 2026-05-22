import {Routes, Route} from 'react-router';
import {Toaster} from 'react-hot-toast';
import Layout from './components/Layout/Layout';
import RequireAuth from './components/RequireAuth';
import {useTheme} from './context/ThemeContext';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ObjectDetailPage from './pages/ObjectDetailPage';
import MyObjectsPage from './pages/MyObjectsPage';
import MyContributionsPage from './pages/MyContributionsPage';
import AddObjectPage from './pages/AddObjectPage';
import EditObjectPage from './pages/EditObjectPage';
import SavedPage from './pages/SavedPage';
import PopularPage from './pages/PopularPage';
import AuthorProfilePage from './pages/AuthorProfilePage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import ReportsCenterPage from './pages/ReportsCenterPage';
import CulturalPassportPage from './pages/CulturalPassportPage';
import RoutesListPage from './pages/RoutesListPage';
import RouteDetailPage from './pages/RouteDetailPage';
import AddEditRoutePage from './pages/AddEditRoutePage';
import MyRoutesPage from './pages/MyRoutesPage';

function App() {
    const {theme} = useTheme();
    const isDark = theme === 'dark';
    return (
        <>
        <Toaster position="top-center" toastOptions={{
            style: {
                borderRadius: '8px',
                background: isDark ? '#1c1917' : '#fffbeb',       /* stone-900 / amber-50 */
                color: isDark ? '#fbbf24' : '#92400e',            /* amber-400 / amber-900 */
                border: isDark ? '1px solid #44403c' : '1px solid #fbbf24',
                maxWidth: '560px',
                wordBreak: 'break-word',
                whiteSpace: 'pre-line',
            },
            success: {duration: 3000, iconTheme: {primary: isDark ? '#f59e0b' : '#d97706', secondary: isDark ? '#1c1917' : '#fffbeb'}},
        }}/>
        <Routes>
            <Route path="/login" element={<LoginPage/>}/>
            <Route path="/register" element={<RegisterPage/>}/>
            <Route path="/verify-email" element={<VerifyEmailPage/>}/>
            <Route path="/forgot-password" element={<ForgotPasswordPage/>}/>
            <Route path="/reset-password" element={<ResetPasswordPage/>}/>
            <Route element={<Layout/>}>
                <Route path="/" element={<HomePage/>}/>
                <Route path="/objects/:id" element={<ObjectDetailPage/>}/>
                <Route path="/popular" element={<PopularPage/>}/>
                <Route path="/authors/:username" element={<AuthorProfilePage/>}/>
                <Route path="/routes" element={<RoutesListPage/>}/>
                <Route path="/routes/:id" element={<RouteDetailPage/>}/>
                <Route element={<RequireAuth/>}>
                    <Route path="/saved" element={<SavedPage/>}/>
                    <Route path="/objects/add" element={<AddObjectPage/>}/>
                    <Route path="/objects/:id/edit" element={<EditObjectPage/>}/>
                    <Route path="/my-objects" element={<MyObjectsPage/>}/>
                    <Route path="/my-contributions" element={<MyContributionsPage/>}/>
                    <Route path="/reports" element={<ReportsCenterPage/>}/>
                    <Route path="/passport" element={<CulturalPassportPage/>}/>
                    <Route path="/my-routes" element={<MyRoutesPage/>}/>
                    <Route path="/routes/add" element={<AddEditRoutePage/>}/>
                    <Route path="/routes/:id/edit" element={<AddEditRoutePage/>}/>
                </Route>
            </Route>
        </Routes>
        </>
    )
}

export default App;
