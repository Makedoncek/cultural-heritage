import {StrictMode} from 'react'
import {createRoot} from 'react-dom/client'
import './index.css'
import './i18n'
import {BrowserRouter} from 'react-router-dom'
import App from './App.tsx'
import {AuthProvider} from "./context/AuthContext.tsx";
import {ThemeProvider} from "./context/ThemeContext.tsx";


createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <ThemeProvider>
            <BrowserRouter>
                <AuthProvider>
                    <App/>
                </AuthProvider>
            </BrowserRouter>
        </ThemeProvider>
    </StrictMode>,
)
