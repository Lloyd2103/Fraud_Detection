import client from './client';

export const verdictsApi = {
  fetchInspectedAlerts: (options = {}) => {
    let params = {};
    if (typeof options === 'object' && options !== null) {
      const {
        page = 1,
        limit = 50,
        search = '',
        channel = 'ALL',
        amountRange = 'ALL',
        label = null,
        inspectorId = null,
        from = null,
        to = null,
      } = options;
      params.page = page;
      params.limit = limit;
      if (search) params.search = search;
      if (channel && channel !== 'ALL') params.channel = channel;
      if (amountRange && amountRange !== 'ALL') params.amount_range = amountRange;
      if (label !== null && label !== undefined && label !== 'ALL') params.label = label;
      if (inspectorId) params.inspector_id = inspectorId;
      if (from) params.from = from;
      if (to) params.to = to;
    }
    return client.get('/alerts/inspected', { params });
  },

  fetchVerdictsStats: (params = {}) => client.get('/verdicts/stats', { params }),

  submitInspection: (transactionId, payload) =>
    client.post(`/transactions/${transactionId}/decision`, payload),
};

export default verdictsApi;

