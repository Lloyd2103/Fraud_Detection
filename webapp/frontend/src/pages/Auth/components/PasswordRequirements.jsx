import React from 'react';
import { CheckCircle2, Circle } from 'lucide-react';

export default function PasswordRequirements({
  pwd,
  pwdScore,
  strengthColors,
  strengthLabels,
  hasLen,
  hasLetter,
  hasDigit,
  hasSpecial,
}) {
  return (
    <>
      {/* Strength Meter Bar */}
      <div style={{ marginTop: '0.25rem' }}>
        <div style={{ display: 'flex', height: '4px', gap: '4px', borderRadius: '2px', overflow: 'hidden' }}>
          {[1, 2, 3, 4].map((idx) => (
            <div
              key={idx}
              style={{
                flex: 1,
                backgroundColor: pwdScore >= idx ? strengthColors[pwdScore] : '#e4e4e7',
                transition: 'background-color 0.2s ease',
              }}
            />
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.3rem' }}>
          <span style={{ fontSize: '0.72rem', color: '#71717a' }}>Strength</span>
          <span style={{ fontSize: '0.72rem', fontWeight: 600, color: strengthColors[pwdScore] }}>
            {pwd.length === 0 ? 'Enter password' : strengthLabels[pwdScore]}
          </span>
        </div>
      </div>

      {/* 4 Rules Checklist */}
      <div style={{
        backgroundColor: '#f4f4f5',
        border: '1px solid #e4e4e7',
        borderRadius: '6px',
        padding: '0.6rem 0.75rem',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '0.4rem',
        marginTop: '0.35rem',
      }}>
        {[
          { label: 'At least 8 chars', ok: hasLen },
          { label: 'Contains letters', ok: hasLetter },
          { label: 'Contains digits', ok: hasDigit },
          { label: 'Special symbol', ok: hasSpecial },
        ].map((rule) => (
          <div key={rule.label} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            {rule.ok ? (
              <CheckCircle2 size={13} strokeWidth={2} style={{ color: '#10b981' }} />
            ) : (
              <Circle size={13} strokeWidth={1.5} style={{ color: '#a1a1aa' }} />
            )}
            <span style={{ fontSize: '0.72rem', color: rule.ok ? '#09090b' : '#71717a', fontWeight: rule.ok ? 500 : 400 }}>
              {rule.label}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

