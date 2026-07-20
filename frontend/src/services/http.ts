import axios from 'axios';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export const http = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
});

http.interceptors.response.use(
  response => response,
  error => Promise.reject(error),
);

export const withBackendAssetUrl = (url?: string) => {
  if (!url || /^https?:\/\//i.test(url)) return url || '';
  if (!url.startsWith('/')) return url;
  return `${API_BASE_URL}${url}`;
};
