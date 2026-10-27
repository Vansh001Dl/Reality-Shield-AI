import React, { useState } from 'react';
import { authService } from '../services/api';

const RegisterPage = ({ onRegisterComplete, onLogin }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const register = async () => {
    setError('');
    setSuccess('');
    setIsLoading(true);

    try {
      const response = await authService.register(username, email, password, fullName);

      if (response.success) {
        setSuccess('Account created successfully! You can now log in.');
        // Auto-switch to login after a delay
        setTimeout(() => {
          if (onLogin) {
            onLogin();
          }
        }, 2000);
      } else {
        setError(response.error || response.message || 'Registration failed');
      }
    } catch (error) {
      setError(error.message || 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="register-page">
      <div className="register-container">
        <div className="register-header">
          <h1>RealityShield-AI</h1>
          <h2>Create Your Account</h2>
        </div>

        {error && <div className="error-banner">{error}</div>}
        {success && <div className="success-banner">{success}</div>}

        <form className="register-form" onSubmit={e => { e.preventDefault(); register(); }}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={50}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="fullName">Full Name</label>
            <input
              type="text"
              id="fullName"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              maxLength={100}
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
              minLength={8}
            />
          </div>

          <button type="submit" className="register-btn" disabled={isLoading}>
            {isLoading ? 'Creating account...' : 'Register'}
          </button>
        </form>

        <div className="register-footer">
          <p>Already have an account?</p>
          <button className="login-link" onClick={onLogin}>
            Sign In
          </button>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;