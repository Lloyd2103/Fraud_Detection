export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/alerts`;

