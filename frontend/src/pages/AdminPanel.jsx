import { useState, useEffect } from 'react';
import { getUsers, createUser, deleteUser, getSheets, updateUserSheets } from '../api';
import './AdminPanel.css';

export default function AdminPanel({ token }) {
    const [users, setUsers] = useState([]);
    const [sheets, setSheets] = useState([]);
    const [selectedUser, setSelectedUser] = useState(null);
    const [error, setError] = useState('');

    // Create user form
    const [newUsername, setNewUsername] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [newRole, setNewRole] = useState('viewer');
    const [creating, setCreating] = useState(false);

    useEffect(() => {
        Promise.all([getUsers(token), getSheets(token)])
            .then(([u, s]) => { setUsers(u); setSheets(s); })
            .catch(err => setError(err.message));
    }, []);

    async function handleCreate(e) {
        e.preventDefault();
        setError('');
        setCreating(true);
        try {
            await createUser(token, newUsername, newPassword, newRole);
            const updated = await getUsers(token);
            setUsers(updated);
            setNewUsername('');
            setNewPassword('');
            setNewRole('viewer');
        } catch (err) {
            setError(err.message);
        } finally {
            setCreating(false);
        }
    }

    async function handleDelete(userId) {
        setError('');
        try {
            await deleteUser(token, userId);
            setUsers(u => u.filter(x => x.id !== userId));
            if (selectedUser?.id === userId) setSelectedUser(null);
        } catch (err) {
            setError(err.message);
        }
    }

    async function handleSheetToggle(sheetId) {
        if (!selectedUser) return;
        const current = selectedUser.sheet_ids;
        const next = current.includes(sheetId)
            ? current.filter(id => id !== sheetId)
            : [...current, sheetId];

        try {
            await updateUserSheets(token, selectedUser.id, next);
            const updated = users.map(u =>
                u.id === selectedUser.id ? { ...u, sheet_ids: next } : u
            );
            setUsers(updated);
            setSelectedUser(u => ({ ...u, sheet_ids: next }));
        } catch (err) {
            setError(err.message);
        }
    }

    return (
        <div className="admin-panel">
            {error && <p className="admin-error">{error}</p>}

            <div className="admin-columns">
                {/* Left: user list */}
                <div className="admin-col">
                    <h2 className="admin-section-title">Usuarios</h2>

                    <ul className="user-list">
                        {users.map(u => (
                            <li
                                key={u.id}
                                className={`user-row ${selectedUser?.id === u.id ? 'selected' : ''}`}
                                onClick={() => setSelectedUser(u)}
                            >
                                <div className="user-info">
                                    <span className="user-name">{u.username}</span>
                                    <span className={`user-role role-${u.role}`}>{u.role}</span>
                                    {u.is_superuser && <span className="superuser-badge" title="Superusuario — no puede ser eliminado">⚿</span>}
                                </div>
                                {!u.is_superuser && (
                                    <button
                                        className="delete-btn"
                                        onClick={e => { e.stopPropagation(); handleDelete(u.id); }}
                                        title="Eliminar usuario"
                                    >
                                        ×
                                    </button>
                                )}
                            </li>
                        ))}
                    </ul>

                    <form className="create-form" onSubmit={handleCreate}>
                        <h3 className="admin-section-title">Nuevo usuario</h3>
                        <input
                            className="admin-input"
                            type="text"
                            placeholder="Usuario"
                            value={newUsername}
                            onChange={e => setNewUsername(e.target.value)}
                            required
                        />
                        <input
                            className="admin-input"
                            type="password"
                            placeholder="Contraseña"
                            value={newPassword}
                            onChange={e => setNewPassword(e.target.value)}
                            required
                        />
                        <select
                            className="admin-input"
                            value={newRole}
                            onChange={e => setNewRole(e.target.value)}
                        >
                            <option value="viewer">viewer</option>
                            <option value="admin">admin</option>
                        </select>
                        <button className="admin-btn" type="submit" disabled={creating}>
                            {creating ? 'Creando...' : 'Crear usuario'}
                        </button>
                    </form>
                </div>

                {/* Right: sheet permissions */}
                <div className="admin-col">
                    <h2 className="admin-section-title">
                        {selectedUser
                            ? `Hojas — ${selectedUser.username}`
                            : 'Selecciona un usuario para gestionar sus permisos'}
                    </h2>

                    {selectedUser && (
                        <ul className="sheet-list">
                            {sheets.map(s => (
                                <li key={s.id} className="sheet-row">
                                    <label className="sheet-label">
                                        <input
                                            type="checkbox"
                                            checked={selectedUser.sheet_ids.includes(s.id)}
                                            onChange={() => handleSheetToggle(s.id)}
                                        />
                                        {s.display_name || s.name}
                                    </label>
                                </li>
                            ))}
                            {sheets.length === 0 && (
                                <p className="admin-empty">Hojas de cálculo no sincronizadas.</p>
                            )}
                        </ul>
                    )}

                    {!selectedUser && (
                        <p className="admin-empty">Selecciona un usuario para gestionar sus permisos.</p>
                    )}
                </div>
            </div>
        </div>
    );
}
