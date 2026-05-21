import {Outlet} from 'react-router';
import Header from './Header';
import Footer from './Footer';

export default function Layout() {
    return (
        <div className="min-h-screen flex flex-col bg-white dark:bg-stone-950 text-gray-900 dark:text-stone-100">
            <Header/>
            <main className="flex-1 flex flex-col">
                <Outlet/>
            </main>
            <Footer/>
        </div>
    );
}
