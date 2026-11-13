import React from 'react';
import { Mail, ArrowRight, ArrowLeft } from 'lucide-react';

export default function ForgotStepEmail({
  email,
  setEmail,
  setError,
  busy,
  onGoLogin,
  handleRequestOtp,
}) {
  return (
    <form onSubmit={handleRequestOtp} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <label htmlFor="reset-email" style={{ fontSize: '0.8125rem', fontWeight: 500, color: '#09090b' }}>
          Work Email
        </label>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Mail size={16} strokeWidth={1.5} style={{ position: 'absolute', left: '0.75rem', color: '#a1a1aa' }} />
          <input
            id="reset-email"
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setError(''); }}
            placeholder="auditor@company.com"
            className="shadcn-input"
            style={{ paddingLeft: '2.25rem' }}
            required
            autoFocus
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={busy}
        className="btn-shadcn btn-primary"
        style={{ width: '100%', height: '2.5rem', marginTop: '0.25rem' }}
      >
        {busy ? (
          'Checking account & sending code...'
        ) : (
          <>
            <span>Send Verification Code</span>
            <ArrowRight size={16} strokeWidth={1.5} />
          </>
        )}
      </button>

      <button
        type="button"
        onClick={() => onGoLogin(email)}
        style={{
          background: 'none',
          border: 'none',
          color: '#71717a',
          fontSize: '0.8125rem',
          fontWeight: 500,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.4rem',
          marginTop: '0.25rem',
          padding: '0.5rem',
        }}
        onMouseEnter={(e) => e.currentTarget.style.color = '#09090b'}
        onMouseLeave={(e) => e.currentTarget.style.color = '#71717a'}
      >
        <ArrowLeft size={15} />
        <span>Back to Sign In</span>
      </button>
    </form>
  );
}

