export const ROUTES = {
  ALERT_QUEUE: '/alerts',
  INSPECTED_VERDICTS: '/inspected',
  TX_DETAIL: '/transactions/:id',
  FRAUD_SUMMARY: '/fraud-summary',
  MODEL_PERFORMANCE: '/model-governance',
  DELTA_AUDIT: '/audit',
  LATENCY: '/latency',
  DELTA_CONFIG: '/delta-config',
  TEAM_ROLES: '/team-roles',
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
};

export const TAB_LABELS = {
  alerts: 'Alert Queue',
  inspected: 'Inspected Verdicts',
  'fraud-summary': 'Fraud Summary',
  detail: 'Details & Inspection',
  models: 'Model Performance & Drift',
  audit: 'Delta Time Travel & Audit',
  latency: 'Latency Monitoring (SLA)',
  team: 'Team & Roles',
  'delta-config': 'Delta Lake Config',
};
