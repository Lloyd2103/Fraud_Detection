import client from './client';

export const auditApi = {
  fetchTimeTravel: (version, config = {}) =>
    client.get(`/audit/time-travel/${version}`, config),
  fetchDeltaCommits: (limit = 145) =>
    client.get('/audit/commits', { params: { limit } }),
  rerunAuditEvaluation: (version, params = {}) =>
    client.post(`/audit/rerun-eval/${version}`, null, { params }),
  fetchAuditTrail: (limit = 50) =>
    client.get('/audit/trail', { params: { limit } }),
};

export default auditApi;

