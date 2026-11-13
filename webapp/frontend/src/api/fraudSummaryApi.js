import client from './client';

export const fraudSummaryApi = {
  fetchFraudSummary: (params = {}) => client.get('/fraud-summary', { params }),
  fetchFraudSummaryOverall: () => client.get('/fraud-summary/overall'),
  recalculateFraudSummary: () => client.post('/fraud-summary/recalculate'),
};

export default fraudSummaryApi;

