import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { User, Mail, Shield, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react';
import RegisterHeader from './components/RegisterHeader';
import RegisterPasswordFields from './components/RegisterPasswordFields';

export default function RegisterPage({ onGoLogin, defaultEmail = '' }) {
  const { register } = useAuth();

  const [form, setForm] = useState({
    full_name: '',
    email: defaultEmail,
    role: 'auditor',
    password: '',
    confirm: '',
  });

  const [showPwd, setShowPwd] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);

  const update = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    if (error) setError('');
  };

  // Password rules validation
  const pwd = form.password;
  const hasLen = pwd.length >= 8;
  const hasLetter = /[a-zA-Z]/.test(pwd);
  const hasDigit = /\d/.test(pwd);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/`~]/.test(pwd);
  const pwdScore = [hasLen, hasLetter, hasDigit, hasSpecial].filter(Boolean).length;
  const isPwdValid = pwdScore === 4;

  const isMatch = form.confirm.length > 0 && form.password === form.confirm;
  const matchMismatch = form.confirm.length > 0 && form.password !== form.confirm;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.full_name.trim()) {
      setError('Please enter your full name.');
      return;
    }
    if (!form.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setError('Please enter a valid email address.');
      return;
    }
    if (!isPwdValid) {
      setError('Password must meet all 4 criteria: 8+ chars, letters, numbers, and special symbols.');
      return;
    }
    if (form.password !== form.confirm) {
      setError('Password and confirmation do not match.');
      return;
    }

    setBusy(true);
    setError('');
    setSuccess('');
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
        role: form.role,
      });

      setSuccess('Registration successful! Your account is pending Administrator approval before you can sign in.');
      setTimeout(() => {
        onGoLogin(form.email.trim().toLowerCase());
      }, 3000);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Registration failed. Please check your details.';
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  const strengthColors = ['#e4e4e7', '#ef4444', '#f59e0b', '#3b82f6', '#10b981'];
  const strengthLabels = ['Empty', 'Very Weak', 'Moderate', 'Strong', 'All Criteria Met'];

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#fafafa',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem 1.5rem',
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    }}>
      <div style={{
        width: '100%',
        maxWidth: '460px',
        backgroundColor: '#ffffff',
        border: '1px solid #e4e4e7',
        borderRadius: '8px',
        padding: '2rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
      }}>
        <RegisterHeader email={form.email} onGoLogin={onGoLogin} />

        {/* Alerts */}
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

        {success && (
          <div style={{
            backgroundColor: '#f0fdf4',
            border: '1px solid #dcfce7',
            borderRadius: '8px',
            padding: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: '#166534',
            fontSize: '0.8125rem',
          }}>
            <CheckCircle2 size={16} strokeWidth={1.75} style={{ flexShrink: 0 }} />
            <span>{success}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Full Name */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            <label htmlFor="reg-name" style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#09090b' }}>
              Full Name <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <User size={16} strokeWidth={1.5} style={{ position: 'absolute', left: '0.75rem', color: '#a1a1aa' }} />
              <input
                id="reg-name"
                type="text"
                value={form.full_name}
                onChange={update('full_name')}
                placeholder="e.g. Senior Auditor Nam"
                className="shadcn-input"
                style={{ paddingLeft: '2.25rem' }}
                required
                autoFocus
              />
            </div>
          </div>

          {/* Email */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            <label htmlFor="reg-email" style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#09090b' }}>
              Work Email <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Mail size={16} strokeWidth={1.5} style={{ position: 'absolute', left: '0.75rem', color: '#a1a1aa' }} />
              <input
                id="reg-email"
                type="email"
                value={form.email}
                onChange={update('email')}
                placeholder="auditor@company.com"
                className="shadcn-input"
                style={{ paddingLeft: '2.25rem' }}
                autoComplete="email"
                required
              />
            </div>
          </div>

          {/* Role Info Notice */}
          <div style={{
            backgroundColor: '#eff6ff',
            border: '1px solid #dbeafe',
            borderRadius: '6px',
            padding: '0.65rem 0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.75rem',
            color: '#1e40af',
          }}>
            <Shield size={15} strokeWidth={1.75} style={{ color: '#2563eb', flexShrink: 0 }} />
            <span>New accounts require Administrator approval. An Admin will review and activate your account before you can sign in.</span>
          </div>

          <RegisterPasswordFields
            password={form.password}
            confirm={form.confirm}
            update={update}
            showPwd={showPwd}
            setShowPwd={setShowPwd}
            showConfirm={showConfirm}
            setShowConfirm={setShowConfirm}
            pwdScore={pwdScore}
            strengthColors={strengthColors}
            strengthLabels={strengthLabels}
            hasLen={hasLen}
            hasLetter={hasLetter}
            hasDigit={hasDigit}
            hasSpecial={hasSpecial}
            isMatch={isMatch}
            matchMismatch={matchMismatch}
          />

          {/* Submit */}
          <button
            type="submit"
            id="btn-register-submit"
            disabled={busy || !isPwdValid || !isMatch}
            className="btn-shadcn btn-primary"
            style={{
              width: '100%',
              height: '2.5rem',
              marginTop: '0.25rem',
              opacity: (!isPwdValid || !isMatch) ? 0.6 : 1,
              cursor: (!isPwdValid || !isMatch) ? 'not-allowed' : 'pointer',
            }}
          >
            {busy ? (
              'Creating Account...'
            ) : (
              <>
                <span>Complete Registration</span>
                <ArrowRight size={16} strokeWidth={1.5} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
