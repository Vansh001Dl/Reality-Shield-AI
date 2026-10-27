import axios from 'axios';
import authServiceInstance from './authService.js';

// Create base API instance
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001',
  timeout: 10000,
});

// Authenticated API instance
export const authenticatedApi = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001',
  timeout: 120000,
});

// Request interceptor for authenticated API
authenticatedApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for token refresh
authenticatedApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle token expiration
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(
            `${api.defaults.baseURL}/api/auth/refresh`,
            null,
            { params: { refresh_token: refreshToken } }
          );

          const { access_token, refresh_token: nextRefreshToken } = response.data;
          localStorage.setItem('access_token', access_token);
          if (nextRefreshToken) {
            localStorage.setItem('refresh_token', nextRefreshToken);
          }

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return authenticatedApi(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export const authService = authServiceInstance;
export const videoApi = authenticatedApi;

export default api;
