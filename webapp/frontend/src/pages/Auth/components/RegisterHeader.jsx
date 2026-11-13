import React from 'react';
import { Shield } from 'lucide-react';

export default function RegisterHeader({ email, onGoLogin }) {
  return (
    <>
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
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.02em' }}>
            Create Account
          </h1>
          <p style={{ fontSize: '0.8125rem', color: '#71717a', marginTop: '0.2rem' }}>
            Fraud Detection • Real-Time Lakehouse Platform
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
          onClick={() => onGoLogin(email)}
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
          onMouseEnter={(e) => e.currentTarget.style.color = '#09090b'}
          onMouseLeave={(e) => e.currentTarget.style.color = '#71717a'}
        >
          Sign In
        </button>
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
          Create Account
        </button>
      </div>
    </>
  );
}

