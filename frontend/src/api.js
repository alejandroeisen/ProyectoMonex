const BASE_URL = 'http://localhost:8000';

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
