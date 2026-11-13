export const ROLES = {
  ADMIN: 'admin',
  ANALYST: 'analyst',
  AUDITOR: 'auditor',
};

export const ROLE_HIERARCHY = {
  admin: ['admin', 'analyst', 'auditor'],
  analyst: ['analyst', 'auditor'],
  auditor: ['auditor'],
};

export const ROLE_ALLOWED_TABS = {
  auditor: ['alerts', 'inspected', 'fraud-summary', 'detail'],
  analyst: ['models', 'audit', 'latency', 'delta-config'],
  admin:   ['alerts', 'inspected', 'fraud-summary', 'detail', 'models', 'audit', 'latency', 'team', 'delta-config'],
};

export const ROLE_BADGE_STYLE = {
  admin:   { color: '#991b1b', bg: '#fef2f2', border: '#fee2e2' },
  auditor: { color: '#6b21a8', bg: '#faf5ff', border: '#f3e8ff' },
  analyst: { color: '#0e7490', bg: '#ecfeff', border: '#cffafe' },
};

export const getDefaultTabForRole = (role) => {
  switch (role) {
    case 'auditor': return 'alerts';
    case 'analyst': return 'models';
    case 'admin': return 'fraud-summary';
    default: return 'alerts';
  }
};
