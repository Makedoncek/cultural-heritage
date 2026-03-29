import {Routes, Route} from 'react-router';
import {Toaster} from 'react-hot-toast';
import Layout from './components/Layout/Layout';
import RequireAuth from './components/RequireAuth';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ObjectDetailPage from './pages/ObjectDetailPage';
import MyObjectsPage from './pages/MyObjectsPage';
import AddObjectPage from './pages/AddObjectPage';
import EditObjectPage from './pages/EditObjectPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';

function App() {
    return (
        <>
        <Toaster position="top-center" toastOptions={{
            style: {borderRadius: '8px', background: '#fffbeb', color: '#92400e', border: '1px solid #fbbf24'},
            success: {duration: 3000, iconTheme: {primary: '#d97706', secondary: '#fffbeb'}},
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
                <Route element={<RequireAuth/>}>
                    <Route path="/objects/add" element={<AddObjectPage/>}/>
                    <Route path="/objects/:id/edit" element={<EditObjectPage/>}/>
                    <Route path="/my-objects" element={<MyObjectsPage/>}/>
                </Route>
            </Route>
        </Routes>
        </>
    )
}

export default App;
