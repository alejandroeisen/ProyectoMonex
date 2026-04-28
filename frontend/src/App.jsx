import { useState } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

const STORAGE_KEY = 'intelimed_auth';

function loadAuth() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY));
    } catch {
        return null;
    }
}

export default function App() {
    const [auth, setAuth] = useState(loadAuth);

    function handleLogin(data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        setAuth(data);
    }

    function handleLogout() {
        localStorage.removeItem(STORAGE_KEY);
        setAuth(null);
    }

    return (
        <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
            {!auth ? (
                <Login onLogin={handleLogin} />
            ) : (
                <Dashboard
                    user={{ username: auth.username, role: auth.role }}
                    token={auth.access_token}
                    onLogout={handleLogout}
                />
            )}
        </GoogleOAuthProvider>
    );
}
