import {Routes, Route} from 'react-router';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import ObjectDetailPage from './pages/ObjectDetailPage';
import MyObjectsPage from './pages/MyObjectsPage';
import AddObjectPage from './pages/AddObjectPage';
import EditObjectPage from './pages/EditObjectPage.tsx'
import RegisterPage from './pages/RegisterPage'

function App() {
    return (
        <Routes>
            <Route path="/" element={<HomePage/>}/>
            <Route path="/objects/:id" element={<ObjectDetailPage/>}/>
            <Route path="/objects/add" element={<AddObjectPage/>}/>
            <Route path="/objects/:id/edit" element={<EditObjectPage/>}/>
            <Route path="/my-objects" element={<MyObjectsPage/>}/>
            <Route path="/login" element={<LoginPage/>}/>
            <Route path="/register" element={<RegisterPage/>}/>
        </Routes>
    )
}

export default App;
