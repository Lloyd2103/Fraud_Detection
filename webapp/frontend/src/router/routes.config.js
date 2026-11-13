import React from 'react';
import { ROUTES } from '../constants/routes';

export const AlertQueuePage = React.lazy(() => import('../pages/AlertQueue/AlertQueuePage'));
export const InspectedVerdictsPage = React.lazy(() => import('../pages/InspectedVerdicts/InspectedVerdictsPage'));
export const TxDetailPage = React.lazy(() => import('../pages/TxDetail/TxDetailPage'));
export const FraudSummaryPage = React.lazy(() => import('../pages/FraudSummary/FraudSummaryPage'));
export const ModelDashPage = React.lazy(() => import('../pages/ModelPerformance/ModelDashPage'));
export const AuditPage = React.lazy(() => import('../pages/DeltaAudit/AuditPage'));
export const LatencyPage = React.lazy(() => import('../pages/Latency/LatencyPage'));
export const TeamRolesPage = React.lazy(() => import('../pages/TeamRoles/TeamRolesPage'));
export const DeltaConfigPage = React.lazy(() => import('../pages/DeltaConfig/DeltaConfigPage'));

export const routesConfig = [
  {
    path: ROUTES.ALERT_QUEUE,
    key: 'alerts',
    label: 'Alert Queue',
    roles: ['auditor', 'admin'],
    component: AlertQueuePage,
  },
  {
    path: ROUTES.INSPECTED_VERDICTS,
    key: 'inspected',
    label: 'Inspected Verdicts',
    roles: ['auditor', 'admin'],
    component: InspectedVerdictsPage,
  },
  {
    path: ROUTES.TX_DETAIL,
    key: 'detail',
    label: 'Details & Inspection',
    roles: ['auditor', 'admin'],
    component: TxDetailPage,
    hideFromNav: true,
  },
  {
    path: ROUTES.FRAUD_SUMMARY,
    key: 'fraud-summary',
    label: 'Fraud Summary',
    roles: ['auditor', 'admin'],
    component: FraudSummaryPage,
  },
  {
    path: ROUTES.MODEL_PERFORMANCE,
    key: 'models',
    label: 'Model Performance & Drift',
    roles: ['analyst', 'admin'],
    component: ModelDashPage,
  },
  {
    path: ROUTES.DELTA_AUDIT,
    key: 'audit',
    label: 'Delta Time Travel & Audit',
    roles: ['analyst', 'admin'],
    component: AuditPage,
  },
  {
    path: ROUTES.LATENCY,
    key: 'latency',
    label: 'Latency Monitoring (SLA)',
    roles: ['analyst', 'admin'],
    component: LatencyPage,
  },
  {
    path: ROUTES.TEAM_ROLES,
    key: 'team',
    label: 'Team & Roles',
    roles: ['admin'],
    component: TeamRolesPage,
  },
  {
    path: ROUTES.DELTA_CONFIG,
    key: 'delta-config',
    label: 'Delta Lake Config',
    roles: ['analyst', 'admin'],
    component: DeltaConfigPage,
  },
];

export const getRoleAllowedTabsFromRoutes = () => {
  const roles = ['auditor', 'analyst', 'admin'];
  const mapping = {};
  for (const role of roles) {
    mapping[role] = routesConfig
      .filter((route) => route.roles.includes(role))
      .map((route) => route.key);
  }
  return mapping;
};

export default routesConfig;
