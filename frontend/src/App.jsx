import { useState } from 'react';
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

    if (!auth) {
        return <Login onLogin={handleLogin} />;
    }

    return (
        <Dashboard
            user={{ username: auth.username, role: auth.role }}
            token={auth.access_token}
            onLogout={handleLogout}
        />
    );
}
