import React from 'react';
import { Mail, Clock, ArrowRight, ArrowLeft, RefreshCw } from 'lucide-react';

export default function ForgotStepOtp({
  email,
  setStep,
  setError,
  otpCode,
  setOtpCode,
  timeLeft,
  formatTimer,
  busy,
  handleVerifyOtp,
  handleRequestOtp,
}) {
  return (
    <form onSubmit={handleVerifyOtp} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Email Sent Inbox Notice */}
      <div style={{
        backgroundColor: '#eff6ff',
        border: '1px solid #bfdbfe',
        borderRadius: '8px',
        padding: '0.85rem 1rem',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.6rem',
      }}>
        <Mail size={18} style={{ color: '#2563eb', flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '0.8125rem', color: '#1e40af', lineHeight: 1.45 }}>
          A 6-digit code has been dispatched to <strong>{email}</strong>. 
          Please check your <strong>Inbox</strong> (or Spam folder).
        </div>
      </div>

      {/* Email with Change button */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: '#f4f4f5',
        padding: '0.5rem 0.75rem',
        borderRadius: '6px',
        fontSize: '0.8125rem',
        color: '#3f3f46',
      }}>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '240px' }}>
          Email: <strong>{email}</strong>
        </span>
        <button
          type="button"
          onClick={() => { setStep(1); setError(''); }}
          style={{
            background: 'none',
            border: 'none',
            color: '#2563eb',
            fontSize: '0.75rem',
            fontWeight: 600,
            cursor: 'pointer',
            padding: 0,
          }}
        >
          Change
        </button>
      </div>

      {/* 6-digit OTP */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <label htmlFor="otp-input" style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#09090b' }}>
            6-Digit Verification Code
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: timeLeft > 0 ? '#71717a' : '#ef4444' }}>
            <Clock size={12} />
            <span>{timeLeft > 0 ? formatTimer(timeLeft) : 'Expired'}</span>
          </div>
        </div>
        <input
          id="otp-input"
          type="text"
          maxLength={6}
          value={otpCode}
          onChange={(e) => {
            const val = e.target.value.replace(/\D/g, '').slice(0, 6);
            setOtpCode(val);
            setError('');
          }}
          placeholder="• • • • • •"
          className="shadcn-input"
          style={{
            textAlign: 'center',
            fontSize: '1.5rem',
            fontWeight: 700,
            letterSpacing: '0.4em',
            fontFamily: "'JetBrains Mono', monospace",
            height: '3rem',
          }}
          required
          autoFocus
        />
      </div>

      {/* Verify Code Button */}
      <button
        type="submit"
        disabled={busy || otpCode.length !== 6 || timeLeft <= 0}
        className="btn-shadcn btn-primary"
        style={{
          width: '100%',
          height: '2.5rem',
          marginTop: '0.25rem',
          opacity: (otpCode.length !== 6 || timeLeft <= 0) ? 0.6 : 1,
        }}
      >
        {busy ? (
          'Verifying code...'
        ) : (
          <>
            <span>Verify Code &amp; Continue</span>
            <ArrowRight size={16} strokeWidth={1.5} />
          </>
        )}
      </button>

      {/* Resend / Back */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          type="button"
          onClick={() => { setStep(1); setError(''); }}
          style={{
            background: 'none',
            border: 'none',
            color: '#71717a',
            fontSize: '0.8125rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
          }}
        >
          <ArrowLeft size={14} /> Back
        </button>

        <button
          type="button"
          onClick={handleRequestOtp}
          disabled={busy || timeLeft > 540}
          style={{
            background: 'none',
            border: 'none',
            color: timeLeft > 540 ? '#a1a1aa' : '#2563eb',
            fontSize: '0.8125rem',
            fontWeight: 500,
            cursor: timeLeft > 540 ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
          }}
        >
          <RefreshCw size={13} />
          <span>Resend Code</span>
        </button>
      </div>
    </form>
  );
}

