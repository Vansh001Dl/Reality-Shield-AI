import React, { useState, useEffect } from 'react';
import { authService } from '../services/api';

const LoginPage = ({ onLoginComplete, onRegister }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const login = async () => {
    setError('');
    setIsLoading(true);

    try {
      const response = await authService.login(username, password);
      if (!response.success) {
        setError(response.error || 'Login failed');
        return;
      }
      const { access_token, refresh_token, user_id } = response.data;

      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);

      if (onLoginComplete) {
        onLoginComplete({ userId: user_id, username });
      }
    } catch (error) {
      setError(error.message || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async () => {
    if (onRegister) {
      onRegister();
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>RealityShield-AI</h1>
          <h2>Road Safety Analysis Platform</h2>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <form className="login-form" onSubmit={e => { e.preventDefault(); login(); }}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          <button type="submit" className="login-btn" disabled={isLoading}>
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="login-footer">
          <p>Don't have an account?</p>
          <button className="register-link" onClick={handleRegister}>
            Register
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;