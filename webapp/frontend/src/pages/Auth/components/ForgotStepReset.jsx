import React from 'react';
import { Lock, Eye, EyeOff, CheckCircle2, Check } from 'lucide-react';

export default function ForgotStepReset({
  email,
  password,
  setPassword,
  confirmPassword,
  setConfirmPassword,
  showPwd,
  setShowPwd,
  showConfirm,
  setShowConfirm,
  setError,
  busy,
  pwdScore,
  strengthColors,
  strengthLabels,
  hasLen,
  hasLetter,
  hasDigit,
  hasSpecial,
  isPwdValid,
  isMatch,
  handleResetPassword,
}) {
  return (
    <form onSubmit={handleResetPassword} style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
      <div style={{
        backgroundColor: '#f0fdf4',
        border: '1px solid #bbf7d0',
        borderRadius: '8px',
        padding: '0.75rem 1rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        fontSize: '0.8125rem',
        color: '#166534',
      }}>
        <Check size={16} strokeWidth={2.5} style={{ color: '#16a34a', flexShrink: 0 }} />
        <span>Identity verified for <strong>{email}</strong>. Enter your new password below:</span>
      </div>

      {/* New Password */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <label htmlFor="new-password" style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#09090b' }}>
          New Password
        </label>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Lock size={16} strokeWidth={1.5} style={{ position: 'absolute', left: '0.75rem', color: '#a1a1aa' }} />
          <input
            id="new-password"
            type={showPwd ? 'text' : 'password'}
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError(''); }}
            placeholder="Min 8 chars with letter, digit & symbol"
            className="shadcn-input"
            style={{ paddingLeft: '2.25rem', paddingRight: '2.25rem' }}
            required
            autoFocus
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

        {/* Password strength meter */}
        {password.length > 0 && (
          <div style={{ marginTop: '0.2rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            <div style={{ display: 'flex', gap: '4px', height: '4px' }}>
              {[1, 2, 3, 4].map((idx) => (
                <div
                  key={idx}
                  style={{
                    flex: 1,
                    borderRadius: '2px',
                    backgroundColor: idx <= pwdScore ? strengthColors[pwdScore] : '#f4f4f5',
                    transition: 'background-color 0.2s',
                  }}
                />
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#71717a' }}>
              <span>Strength: <strong style={{ color: strengthColors[pwdScore] }}>{strengthLabels[pwdScore]}</strong></span>
              <span>{hasLen && hasLetter && hasDigit && hasSpecial ? '✓ Secure' : '8+ chars, a-Z, 0-9, symbol'}</span>
            </div>
          </div>
        )}
      </div>

      {/* Confirm Password */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <label htmlFor="confirm-password" style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#09090b' }}>
          Confirm New Password
        </label>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Lock size={16} strokeWidth={1.5} style={{ position: 'absolute', left: '0.75rem', color: '#a1a1aa' }} />
          <input
            id="confirm-password"
            type={showConfirm ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(e) => { setConfirmPassword(e.target.value); setError(''); }}
            placeholder="Re-enter new password"
            className="shadcn-input"
            style={{ paddingLeft: '2.25rem', paddingRight: '2.25rem' }}
            required
          />
          <button
            type="button"
            onClick={() => setShowConfirm(!showConfirm)}
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
            {showConfirm ? <EyeOff size={16} strokeWidth={1.5} /> : <Eye size={16} strokeWidth={1.5} />}
          </button>
        </div>
        {confirmPassword.length > 0 && !isMatch && (
          <span style={{ fontSize: '0.7rem', color: '#ef4444' }}>Passwords do not match</span>
        )}
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={busy || !isPwdValid || !isMatch}
        className="btn-shadcn btn-primary"
        style={{
          width: '100%',
          height: '2.5rem',
          marginTop: '0.4rem',
          opacity: (!isPwdValid || !isMatch) ? 0.6 : 1,
        }}
      >
        {busy ? (
          'Saving new password...'
        ) : (
          <>
            <span>Update Password</span>
            <CheckCircle2 size={16} strokeWidth={1.5} />
          </>
        )}
      </button>
    </form>
  );
}

