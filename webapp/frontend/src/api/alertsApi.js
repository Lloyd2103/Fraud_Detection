import client from './client';

export const alertsApi = {
  fetchAlerts: (options = {}) => {
    let params = {};
    if (typeof options === 'object' && options !== null) {
      const {
        page = 1,
        limit = 50,
        search = '',
        channel = 'ALL',
        amountRange = 'ALL',
        minAmount,
        maxAmount,
        sortBy = 'risk_score',
        order = 'desc',
      } = options;
      params.page = page;
      params.limit = limit;
      if (search) params.search = search;
      if (channel && channel !== 'ALL') params.channel = channel;
      if (amountRange && amountRange !== 'ALL') params.amount_range = amountRange;
      if (minAmount !== undefined && minAmount !== null && minAmount !== '') params.min_amount = minAmount;
      if (maxAmount !== undefined && maxAmount !== null && maxAmount !== '') params.max_amount = maxAmount;
      if (sortBy) params.sort_by = sortBy;
      if (order) params.order = order;
    } else {
      params.limit = typeof options === 'number' ? options : 50;
    }
    return client.get('/alerts', { params });
  },

  fetchAlertSummary: (inspectorId = null) => {
    const params = inspectorId ? { inspector_id: inspectorId } : {};
    return client.get('/alerts/summary', { params });
  },

  fetchCdfAlerts: (startingVersion = 0) =>
    client.get('/alerts/cdf', {
      params: { starting_version: startingVersion },
    }),
};

export default alertsApi;

