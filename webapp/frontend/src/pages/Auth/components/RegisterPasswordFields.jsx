import React from 'react';
import { Lock, Eye, EyeOff } from 'lucide-react';
import PasswordRequirements from './PasswordRequirements';

export default function RegisterPasswordFields({
  password,
  confirm,
  update,
  showPwd,
  setShowPwd,
  showConfirm,
  setShowConfirm,
  pwdScore,
  strengthColors,
  strengthLabels,
  hasLen,
  hasLetter,
  hasDigit,
  hasSpecial,
  isMatch,
  matchMismatch,
}) {
  return (
    <>
      {/* Password */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        <label htmlFor="reg-password" style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#09090b' }}>
          Password <span style={{ color: '#ef4444' }}>*</span>
        </label>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Lock size={16} strokeWidth={1.5} style={{ position: 'absolute', left: '0.75rem', color: '#a1a1aa' }} />
          <input
            id="reg-password"
            type={showPwd ? 'text' : 'password'}
            value={password}
            onChange={update('password')}
            placeholder="Min 8 chars, letters, numbers & symbols"
            className="shadcn-input"
            style={{ paddingLeft: '2.25rem', paddingRight: '2.25rem' }}
            autoComplete="new-password"
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

        <PasswordRequirements
          pwd={password}
          pwdScore={pwdScore}
          strengthColors={strengthColors}
          strengthLabels={strengthLabels}
          hasLen={hasLen}
          hasLetter={hasLetter}
          hasDigit={hasDigit}
          hasSpecial={hasSpecial}
        />
      </div>

      {/* Confirm Password */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        <label htmlFor="reg-confirm" style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#09090b' }}>
          Confirm Password <span style={{ color: '#ef4444' }}>*</span>
        </label>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Lock size={16} strokeWidth={1.5} style={{ position: 'absolute', left: '0.75rem', color: '#a1a1aa' }} />
          <input
            id="reg-confirm"
            type={showConfirm ? 'text' : 'password'}
            value={confirm}
            onChange={update('confirm')}
            placeholder="Re-enter your password"
            className="shadcn-input"
            style={{
              paddingLeft: '2.25rem',
              paddingRight: '2.25rem',
              borderColor: isMatch ? '#10b981' : (matchMismatch ? '#ef4444' : '#e4e4e7'),
            }}
            autoComplete="new-password"
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
        {matchMismatch && (
          <span style={{ fontSize: '0.72rem', color: '#ef4444' }}>
            Passwords do not match
          </span>
        )}
        {isMatch && (
          <span style={{ fontSize: '0.72rem', color: '#10b981' }}>
            ✓ Passwords match
          </span>
        )}
      </div>
    </>
  );
}

