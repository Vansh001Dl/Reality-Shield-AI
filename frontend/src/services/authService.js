// AuthService for RealityShield-AI frontend
// Handles user authentication, token management, and user session

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001';

class AuthService {
  constructor() {
    this.user = null;
    this.token = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
    this.loadUser();
  }

  loadUser() {
    try {
      const user = localStorage.getItem('user');
      if (user) {
        this.user = JSON.parse(user);
      }
    } catch (error) {
      console.error('Error loading user:', error);
      this.user = null;
    }
  }

  async login(username, password) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
        username,
        password
      });

      const { access_token, refresh_token, user_id } = response.data;

      this.token = access_token;
      this.refreshToken = refresh_token;

      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);

      // Load user info
      const userResult = await this.loadUserInfo();
      if (!userResult.success) {
        return { success: false, error: userResult.error };
      }

      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || error.response?.data?.message || 'Login failed' };
    }
  }

  async register(username, email, password, full_name = null) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
        username,
        email,
        password,
        full_name
      });

      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || error.response?.data?.message || 'Registration failed' };
    }
  }

  async refreshAccessToken() {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/auth/refresh`,
        null,
        { params: { refresh_token: this.refreshToken } }
      );

      const { access_token, refresh_token } = response.data;

      this.token = access_token;
      this.refreshToken = refresh_token || this.refreshToken;

      localStorage.setItem('access_token', access_token);
      if (this.refreshToken) {
        localStorage.setItem('refresh_token', this.refreshToken);
      }

      return { success: true, data: response.data };
    } catch (error) {
      this.logout();
      return { success: false, error: error.response?.data?.detail || error.response?.data?.message || 'Token refresh failed' };
    }
  }

  async loadUserInfo() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/auth/verify`, {
        headers: { Authorization: `Bearer ${this.token}` }
      });

      const user = response.data.user_info;
      this.user = user;
      localStorage.setItem('user', JSON.stringify(user));

      return { success: true, user };
    } catch (error) {
      console.error('Error loading user info:', error);
      this.logout();
      return { success: false, error: error.response?.data?.detail || error.response?.data?.message || 'Failed to load user info' };
    }
  }

  logout() {
    this.user = null;
    this.token = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }

  isAuthenticated() {
    if (!this.token) return false;

    try {
      const tokenParts = this.token.split('.');
      if (tokenParts.length !== 3) return false;

      const payload = JSON.parse(atob(tokenParts[1]));
      const now = Math.floor(Date.now() / 1000);

      return payload.exp > now;
    } catch (error) {
      return false;
    }
  }

  getCurrentUser() {
    return this.user;
  }

  getToken() {
    return this.token;
  }

  getRefreshToken() {
    return this.refreshToken;
  }
}

export default new AuthService();