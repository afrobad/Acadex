
const BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export async function apiRequest(path, options = {}) {
    const token = sessionStorage.getItem('acadex_access_token');

    const headers = {
        ...(options.body
            ? { 'Content-Type': 'application/json' }
            : {}),
        ...(token
            ? { Authorization: `Bearer ${token}` }
            : {}),
        ...options.headers
    };

    const res = await fetch(`${BASE}${path}`, {
        ...options,
        headers
    });

    const type = res.headers.get('content-type') || '';

    const data = type.includes('application/json')
        ? await res.json()
        : await res.text();

    if (!res.ok) {
        throw new Error(
            typeof data === 'object'
                ? (data.message || data.error || `HTTP ${res.status}`)
                : (data || `HTTP ${res.status}`)
        );
    }

    return data;
}
