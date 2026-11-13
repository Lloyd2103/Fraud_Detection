import React from 'react';
import { Shield } from 'lucide-react';

export default function LoadingSplash() {
  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#fafafa',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '1rem',
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    }}>
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
      <p style={{ color: '#71717a', fontSize: '0.875rem', fontWeight: 500 }}>
        Fraud Detection &bull; Verifying session...
      </p>
      <div style={{ width: '160px', height: '2px', backgroundColor: '#e4e4e7', overflow: 'hidden', borderRadius: '1px' }}>
        <div style={{
          height: '100%',
          width: '50%',
          backgroundColor: '#09090b',
          animation: 'load-slide 1.2s infinite ease-in-out',
        }} />
      </div>
      <style>{`
        @keyframes load-slide {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(250%); }
        }
      `}</style>
    </div>
  );
}

