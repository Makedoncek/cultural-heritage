import {Routes, Route} from 'react-router';
import Layout from './components/Layout/Layout';
import RequireAuth from './components/RequireAuth';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ObjectDetailPage from './pages/ObjectDetailPage';
import MyObjectsPage from './pages/MyObjectsPage';
import AddObjectPage from './pages/AddObjectPage';
import EditObjectPage from './pages/EditObjectPage';

function App() {
    return (
        <Routes>
            <Route path="/login" element={<LoginPage/>}/>
            <Route path="/register" element={<RegisterPage/>}/>
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
    )
}

export default App;
