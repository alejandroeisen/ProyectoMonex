import { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { login, loginWithGoogle } from '../api';
import './Login.css';

export default function Login({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [showAdminForm, setShowAdminForm] = useState(false);

    async function handleSubmit(e) {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const data = await login(username, password);
            onLogin(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    async function handleGoogleSuccess(credentialResponse) {
        setError('');
        setLoading(true);
        try {
            const data = await loginWithGoogle(credentialResponse.credential);
            onLogin(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="login-wrapper">
            <div className="login-card">
                <h1>Monex</h1>
                <p className="login-subtitle">Dashboard Interno</p>

                <div className="login-google">
                    <GoogleLogin
                        onSuccess={handleGoogleSuccess}
                        onError={() => setError('Error al iniciar sesión con Google.')}
                        text="signin_with"
                        shape="rectangular"
                        locale="es"
                    />
                </div>

                {error && <p className="login-error">{error}</p>}

                <div className="login-admin-toggle">
                    <button
                        className="login-admin-link"
                        onClick={() => setShowAdminForm(v => !v)}
                        type="button"
                    >
                        {showAdminForm ? 'Ocultar acceso de administrador' : 'Acceso de administrador'}
                    </button>
                </div>

                {showAdminForm && (
                    <form className="login-admin-form" onSubmit={handleSubmit}>
                        <div className="field">
                            <label>Usuario</label>
                            <input
                                type="text"
                                value={username}
                                onChange={e => setUsername(e.target.value)}
                                required
                            />
                        </div>
                        <div className="field">
                            <label>Contraseña</label>
                            <input
                                type="password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                required
                            />
                        </div>
                        <button type="submit" disabled={loading}>
                            {loading ? 'Iniciando sesión...' : 'Iniciar sesión'}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
}
