import {useAuth} from "../context/AuthContext.tsx";

function HomePage() {
    const {user, isAuthenticated, loading} = useAuth();

    if (loading) return <p>Loading...</p>;
    return (
        <div className="p-4">
            <h1 className="text-2xl font-bold">Головна сторінка</h1>
            <p>Auth: {isAuthenticated ? `Logged in as ${user?.username}` : 'Guest'}</p>
        </div>
    );
}

export default HomePage;