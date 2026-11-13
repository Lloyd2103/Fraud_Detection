import React, { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Mail, Lock, Eye, EyeOff, ArrowRight, Shield, AlertCircle } from 'lucide-react';

export default function LoginPage({ onGoRegister, onGoForgotPassword, prefilledEmail = '' }) {
  const { login } = useAuth();
  const [email, setEmail] = useState(prefilledEmail);
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (prefilledEmail) {
      setEmail(prefilledEmail);
    }
  }, [prefilledEmail]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Please enter both your email address and password.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await login(email.trim().toLowerCase(), password);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Invalid email or password!';
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#fafafa',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1.5rem',
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    }}>
      <div style={{
        width: '100%',
        maxWidth: '420px',
        backgroundColor: '#ffffff',
        border: '1px solid #e4e4e7',
        borderRadius: '8px',
        padding: '2rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
      }}>
        {/* Brand Header */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '0.5rem' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '8px',
            backgroundColor: '#09090b',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Shield size={20} strokeWidth={1.5} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.02em', fontFamily: "'JetBrains Mono', monospace" }}>
              Fraud Detection
            </h1>
            <p style={{ fontSize: '0.8125rem', color: '#71717a', marginTop: '0.2rem' }}>
              Real-Time Lakehouse Fraud Inspection Center
            </p>
          </div>
        </div>

        {/* Segmented Tab Switch */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          backgroundColor: '#f4f4f5',
          padding: '3px',
          borderRadius: '8px',
          border: '1px solid #e4e4e7',
        }}>
          <button
            type="button"
            style={{
              padding: '0.45rem',
              fontSize: '0.8125rem',
              fontWeight: 600,
              backgroundColor: '#ffffff',
              color: '#09090b',
              border: '1px solid #e4e4e7',
              borderRadius: '6px',
              cursor: 'default',
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => onGoRegister(email)}
            style={{
              padding: '0.45rem',
              fontSize: '0.8125rem',
              fontWeight: 500,
              backgroundColor: 'transparent',
              color: '#71717a',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              transition: 'color 0.15s ease',
            }}
            onMouseEnter={e => e.currentTarget.style.color = '#09090b'}
            onMouseLeave={e => e.currentTarget.style.color = '#71717a'}
          >
            Create Account
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fee2e2',
            borderRadius: '8px',
            padding: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: '#991b1b',
            fontSize: '0.8125rem',
          }}>
            <AlertCircle size={16} strokeWidth={1.75} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
          {/* Email */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            <label htmlFor="login-email" style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#09090b' }}>
              Work Email
            </label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Mail size={16} strokeWidth={1.5} style={{ position: 'absolute', left: '0.75rem', color: '#a1a1aa' }} />
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={e => { setEmail(e.target.value); setError(''); }}
                placeholder="auditor@company.com"
                className="shadcn-input"
                style={{ paddingLeft: '2.25rem' }}
                autoComplete="email"
                required
                autoFocus
              />
            </div>
          </div>

          {/* Password */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="login-password" style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#09090b' }}>
                Password
              </label>
              {onGoForgotPassword && (
                <button
                  type="button"
                  onClick={() => onGoForgotPassword(email)}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: 0,
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    color: '#2563eb',
                    cursor: 'pointer',
                    transition: 'color 0.15s ease',
                  }}
                  onMouseEnter={e => e.currentTarget.style.color = '#1d4ed8'}
                  onMouseLeave={e => e.currentTarget.style.color = '#2563eb'}
                >
                  Forgot password?
                </button>
              )}
            </div>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Lock size={16} strokeWidth={1.5} style={{ position: 'absolute', left: '0.75rem', color: '#a1a1aa' }} />
              <input
                id="login-password"
                type={showPwd ? 'text' : 'password'}
                value={password}
                onChange={e => { setPassword(e.target.value); setError(''); }}
                placeholder="Enter account password"
                className="shadcn-input"
                style={{ paddingLeft: '2.25rem', paddingRight: '2.25rem' }}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPwd(!showPwd)}
                style={{
                  position: 'absolute',
                  right: '0.75rem',
                  background: 'none',
                  border: 'none',
                  color: '#a1a1aa',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                }}
                tabIndex={-1}
              >
                {showPwd ? <EyeOff size={16} strokeWidth={1.5} /> : <Eye size={16} strokeWidth={1.5} />}
              </button>
            </div>
          </div>

          {/* Remember me checkbox */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              id="remember"
              type="checkbox"
              checked={rememberMe}
              onChange={e => setRememberMe(e.target.checked)}
              style={{
                width: '15px',
                height: '15px',
                borderRadius: '4px',
                accentColor: '#09090b',
                cursor: 'pointer',
              }}
            />
            <label htmlFor="remember" style={{ fontSize: '0.8125rem', color: '#71717a', cursor: 'pointer' }}>
              Keep session active
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            id="btn-login-submit"
            disabled={busy}
            className="btn-shadcn btn-primary"
            style={{ width: '100%', height: '2.5rem', marginTop: '0.25rem' }}
          >
            {busy ? (
              'Authenticating...'
            ) : (
              <>
                <span>Sign In to Dashboard</span>
                <ArrowRight size={16} strokeWidth={1.5} />
              </>
            )}
          </button>
        </form>

        {/* Footer info */}
        <div style={{ borderTop: '1px solid #e4e4e7', paddingTop: '1rem', textAlign: 'center' }}>
          <p style={{ fontSize: '0.75rem', color: '#a1a1aa' }}>
            Protected by PBKDF2 / Bcrypt &amp; Delta Lake RBAC security policy
          </p>
        </div>
      </div>
    </div>
  );
}
