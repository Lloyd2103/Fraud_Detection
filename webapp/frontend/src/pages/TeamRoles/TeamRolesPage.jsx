import React, { useState, useEffect, useCallback } from 'react';
import { useUsers } from '../../hooks/useUsers';
import { Users, Search, RotateCw } from 'lucide-react';
import UserTableRow from './components/UserTableRow';

export default function TeamRolesPage() {
  const { getUsers, updateRoleStatus } = useUsers();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [actionBusyId, setActionBusyId] = useState(null);

  const loadUsers = useCallback(async () => {
    try {
      setRefreshing(true);
      const data = await getUsers();
      if (data) {
        setUsers(data);
      }
    } catch (err) {
      console.error('Error fetching users:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [getUsers]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleRoleChange = async (userId, newRole, currentRole, username) => {
    if (newRole === currentRole) return;
    const ok = window.confirm(`Confirm changing role for user "${username}" from ${currentRole} to ${newRole}?`);
    if (!ok) return;
    setActionBusyId(userId);
    try {
      await updateRoleStatus(userId, { role: newRole });
      await loadUsers();
    } catch (err) {
      alert(`Error updating role: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setActionBusyId(null);
    }
  };

  const handleToggleStatus = async (userId, currentStatus, username) => {
    const nextStatus = currentStatus === 'active' ? 'disabled' : 'active';
    const actionText = nextStatus === 'active' ? 'activate' : 'deactivate';
    const ok = window.confirm(`Confirm to ${actionText} account "${username}"?`);
    if (!ok) return;
    setActionBusyId(userId);
    try {
      await updateRoleStatus(userId, { status: nextStatus });
      await loadUsers();
    } catch (err) {
      alert(`Error updating status: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setActionBusyId(null);
    }
  };

  const filteredUsers = users.filter((u) => {
    const q = searchQuery.toLowerCase().trim();
    return (
      String(u.id).includes(q) ||
      (u.full_name && u.full_name.toLowerCase().includes(q)) ||
      (u.username && u.username.toLowerCase().includes(q)) ||
      (u.email && u.email.toLowerCase().includes(q)) ||
      (u.role && u.role.toLowerCase().includes(q))
    );
  });

  const adminCount = users.filter((u) => u.role === 'admin').length;
  const auditorCount = users.filter((u) => u.role === 'auditor').length;
  const activeCount = users.filter((u) => u.status === 'active').length;

  return (
    <div style={{ padding: '1.5rem', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 500, color: '#71717a', marginBottom: '0.25rem' }}>
            Home &gt; System &gt; Team &amp; Roles
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#09090b', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Users size={24} style={{ color: '#4f46e5' }} />
            Banking Fraud Team &amp; Role Management
          </h1>
          <p style={{ fontSize: '0.8125rem', color: '#71717a', margin: '0.25rem 0 0 0' }}>
            List of fraud auditors, role authorization, and auditor ID reference.
          </p>
        </div>
        <button
          onClick={loadUsers}
          disabled={refreshing}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.45rem 0.85rem',
            fontSize: '0.8125rem',
            fontWeight: 500,
            borderRadius: '6px',
            backgroundColor: '#ffffff',
            border: '1px solid #e4e4e7',
            color: '#09090b',
            cursor: refreshing ? 'not-allowed' : 'pointer',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
          }}
        >
          <RotateCw size={14} className={refreshing ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ backgroundColor: '#ffffff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#71717a', textTransform: 'uppercase' }}>Total Staff Members</div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#09090b', marginTop: '0.5rem' }}>{users.length}</div>
          <div style={{ fontSize: '0.75rem', color: '#16a34a', marginTop: '0.25rem' }}>● {activeCount} Active in system</div>
        </div>
        <div style={{ backgroundColor: '#ffffff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#71717a', textTransform: 'uppercase' }}>Administrators</div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#09090b', marginTop: '0.5rem' }}>{adminCount}</div>
          <div style={{ fontSize: '0.75rem', color: '#6366f1', marginTop: '0.25rem' }}>Full management privileges</div>
        </div>
        <div style={{ backgroundColor: '#ffffff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#71717a', textTransform: 'uppercase' }}>Fraud Auditors</div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#09090b', marginTop: '0.5rem' }}>{auditorCount}</div>
          <div style={{ fontSize: '0.75rem', color: '#0ea5e9', marginTop: '0.25rem' }}>Alert inspection &amp; verdicts</div>
        </div>
      </div>

      <div style={{ backgroundColor: '#ffffff', border: '1px solid #e4e4e7', borderRadius: '8px', overflow: 'hidden' }}>
        <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #e4e4e7', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ position: 'relative', width: '320px' }}>
            <Search size={14} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#a1a1aa' }} />
            <input
              type="text"
              placeholder="Search by ID, name, email or role..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                height: '32px',
                padding: '0 0.75rem 0 2.2rem',
                fontSize: '0.8125rem',
                border: '1px solid #e4e4e7',
                borderRadius: '6px',
                outline: 'none',
              }}
            />
          </div>
          <div style={{ fontSize: '0.8125rem', color: '#71717a', marginLeft: 'auto' }}>
            Showing <strong>{filteredUsers.length}</strong> of <strong>{users.length}</strong> users
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
            <thead>
              <tr style={{ backgroundColor: '#f9fafb', borderBottom: '1px solid #e4e4e7', color: '#71717a', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <th style={{ padding: '0.75rem 1rem' }}>Auditor ID</th>
                <th style={{ padding: '0.75rem 1rem' }}>Staff Member</th>
                <th style={{ padding: '0.75rem 1rem' }}>Email Address</th>
                <th style={{ padding: '0.75rem 1rem' }}>System Role</th>
                <th style={{ padding: '0.75rem 1rem' }}>Status</th>
                <th style={{ padding: '0.75rem 1rem' }}>Created At</th>
                <th style={{ padding: '0.75rem 1rem' }}>Last Login</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: '#71717a' }}>
                    Loading staff members...
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: '#71717a' }}>
                    No staff members found matching "{searchQuery}"
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => (
                  <UserTableRow
                    key={u.id}
                    user={u}
                    actionBusyId={actionBusyId}
                    handleRoleChange={handleRoleChange}
                    handleToggleStatus={handleToggleStatus}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

