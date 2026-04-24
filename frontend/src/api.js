const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
    const res = await fetch(`${BASE_URL}${path}`, options);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail || 'Request failed');
    }
    return res.json();
}

function authHeaders(token) {
    return { 'Authorization': `Bearer ${token}` };
}

export async function login(username, password) {
    return request('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });
}

export async function getSheets(token) {
    return request('/sheets/', { headers: authHeaders(token) });
}

export async function getSheetData(token, sheetId) {
    return request(`/sheets/${sheetId}/data`, { headers: authHeaders(token) });
}

export async function getUsers(token) {
    return request('/admin/users', { headers: authHeaders(token) });
}

export async function createUser(token, username, password, role = 'viewer') {
    return request('/admin/users', {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role }),
    });
}

export async function deleteUser(token, userId) {
    const res = await fetch(`${BASE_URL}/admin/users/${userId}`, {
        method: 'DELETE',
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail || 'Request failed');
    }
}

export async function getStatus(token) {
    return request('/admin/status', { headers: authHeaders(token) });
}

export async function updateUserSheets(token, userId, sheetIds) {
    return request(`/admin/users/${userId}/sheets`, {
        method: 'PUT',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheet_ids: sheetIds }),
    });
}
