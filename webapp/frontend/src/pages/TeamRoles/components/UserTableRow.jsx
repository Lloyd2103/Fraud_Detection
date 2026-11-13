import React from 'react';
import { Power } from 'lucide-react';
import { formatVietnamTime } from '../../../utils/formatters';

export default function UserTableRow({
  user,
  actionBusyId,
  handleRoleChange,
  handleToggleStatus,
}) {
  const initial = (user.full_name || user.username || 'U')[0].toUpperCase();
  const isAdmin = user.role === 'admin';

  return (
    <tr style={{ borderBottom: '1px solid #f4f4f5' }}>
      <td style={{ padding: '0.85rem 1rem' }}>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0.2rem 0.55rem',
          backgroundColor: '#f4f4f5',
          border: '1px solid #e4e4e7',
          borderRadius: '6px',
          fontFamily: "'JetBrains Mono', monospace",
          fontWeight: 700,
          fontSize: '0.8125rem',
          color: '#09090b',
        }}>
          #{user.id}
        </span>
      </td>

      <td style={{ padding: '0.85rem 1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: isAdmin ? '#4f46e5' : '#0ea5e9',
            color: '#ffffff',
            fontWeight: 700,
            fontSize: '0.8125rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            {initial}
          </div>
          <div>
            <div style={{ fontWeight: 600, color: '#09090b', fontSize: '0.875rem' }}>
              {user.full_name}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontFamily: "'JetBrains Mono', monospace" }}>
              @{user.username}
            </div>
          </div>
        </div>
      </td>

      <td style={{ padding: '0.85rem 1rem', color: '#52525b' }}>
        {user.email}
      </td>

      <td style={{ padding: '0.85rem 1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <select
            value={user.role}
            onChange={(e) => handleRoleChange(user.id, e.target.value, user.role, user.username)}
            disabled={actionBusyId === user.id}
            className="shadcn-input"
            style={{
              padding: '0.2rem 0.5rem',
              fontSize: '0.75rem',
              fontWeight: 600,
              height: '28px',
              width: 'auto',
              cursor: 'pointer',
              backgroundColor: isAdmin ? '#fdf2f8' : '#eff6ff',
              color: isAdmin ? '#be185d' : '#1d4ed8',
              border: '1px solid ' + (isAdmin ? '#fbcfe8' : '#bfdbfe'),
              borderRadius: '4px',
              appearance: 'auto',
            }}
          >
            <option value="auditor">AUDITOR</option>
            <option value="analyst">ANALYST</option>
            <option value="admin">ADMIN</option>
          </select>
        </div>
      </td>

      <td style={{ padding: '0.85rem 1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            fontSize: '0.75rem',
            fontWeight: 500,
            color: user.status === 'active' ? '#15803d' : '#a1a1aa',
            minWidth: '55px',
          }}>
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: user.status === 'active' ? '#22c55e' : '#a1a1aa',
            }} />
            {user.status === 'active' ? 'Active' : 'Disabled'}
          </span>
          <button
            type="button"
            onClick={() => handleToggleStatus(user.id, user.status, user.username)}
            disabled={actionBusyId === user.id}
            className="btn-shadcn"
            style={{
              padding: '0.15rem 0.55rem',
              fontSize: '0.7rem',
              fontWeight: 600,
              borderRadius: '4px',
              backgroundColor: user.status === 'active' ? '#fff1f2' : '#f0fdf4',
              color: user.status === 'active' ? '#e11d48' : '#16a34a',
              border: `1px solid ${user.status === 'active' ? '#fecdd3' : '#bbf7d0'}`,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
            title={user.status === 'active' ? 'Deactivate account' : 'Activate account'}
          >
            <Power size={11} strokeWidth={2.2} />
            <span>{user.status === 'active' ? 'Disable' : 'Enable'}</span>
          </button>
        </div>
      </td>

      <td style={{ padding: '0.85rem 1rem', color: '#71717a', fontSize: '0.75rem' }}>
        {user.created_at ? formatVietnamTime(user.created_at) : '—'}
      </td>

      <td style={{ padding: '0.85rem 1rem', color: '#71717a', fontSize: '0.75rem' }}>
        {user.last_login_at ? formatVietnamTime(user.last_login_at) : 'Never'}
      </td>
    </tr>
  );
}

