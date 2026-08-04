import axios from 'axios';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export const http = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
});

// 新架构接口必须通过独立客户端访问，避免把 /api 与 /api/v2 混在一起。
export const v2Http = axios.create({
  baseURL: `${API_BASE_URL}/api/v2`,
  timeout: 30000,
});

http.interceptors.response.use(
  response => response,
  error => Promise.reject(error),
);

v2Http.interceptors.response.use(
  response => response,
  error => Promise.reject(error),
);

export const withBackendAssetUrl = (url?: string) => {
  if (!url || /^https?:\/\//i.test(url)) return url || '';
  if (!url.startsWith('/')) return url;
  return `${API_BASE_URL}${url}`;
};
