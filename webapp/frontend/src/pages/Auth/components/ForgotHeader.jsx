import React from 'react';
import { KeyRound, Lock } from 'lucide-react';

export default function ForgotHeader({ step, email }) {
  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '0.6rem' }}>
        <div style={{
          width: '44px',
          height: '44px',
          borderRadius: '10px',
          backgroundColor: '#09090b',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          {step === 3 ? <Lock size={22} strokeWidth={1.75} /> : <KeyRound size={22} strokeWidth={1.75} />}
        </div>
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.02em' }}>
            {step === 1 && 'Reset Your Password'}
            {step === 2 && 'Verify Security Code'}
            {step === 3 && 'Create New Password'}
          </h1>
          <p style={{ fontSize: '0.8125rem', color: '#71717a', marginTop: '0.25rem', lineHeight: 1.4 }}>
            {step === 1 && 'Enter your registered work email to receive a 6-digit verification code.'}
            {step === 2 && `Enter the 6-digit code sent to ${email}`}
            {step === 3 && 'Choose a strong, unique password to secure your account.'}
          </p>
        </div>
      </div>

      {/* 3-Step Stepper Progress */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}>
        {/* Step 1 Circle */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.3rem',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: step === 1 ? '#09090b' : '#10b981',
        }}>
          <span style={{
            width: '20px',
            height: '20px',
            borderRadius: '50%',
            backgroundColor: step === 1 ? '#09090b' : '#10b981',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.7rem'
          }}>
            {step > 1 ? '✓' : '1'}
          </span>
          <span>Email</span>
        </div>

        <div style={{ width: '24px', height: '1px', backgroundColor: step >= 2 ? '#09090b' : '#e4e4e7' }} />

        {/* Step 2 Circle */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.3rem',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: step === 2 ? '#09090b' : step > 2 ? '#10b981' : '#a1a1aa',
        }}>
          <span style={{
            width: '20px',
            height: '20px',
            borderRadius: '50%',
            backgroundColor: step === 2 ? '#09090b' : step > 2 ? '#10b981' : '#e4e4e7',
            color: step >= 2 ? '#ffffff' : '#71717a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.7rem'
          }}>
            {step > 2 ? '✓' : '2'}
          </span>
          <span>Verify OTP</span>
        </div>

        <div style={{ width: '24px', height: '1px', backgroundColor: step === 3 ? '#09090b' : '#e4e4e7' }} />

        {/* Step 3 Circle */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.3rem',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: step === 3 ? '#09090b' : '#a1a1aa',
        }}>
          <span style={{
            width: '20px',
            height: '20px',
            borderRadius: '50%',
            backgroundColor: step === 3 ? '#09090b' : '#e4e4e7',
            color: step === 3 ? '#ffffff' : '#71717a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.7rem'
          }}>
            3
          </span>
          <span>New Password</span>
        </div>
      </div>
    </>
  );
}

