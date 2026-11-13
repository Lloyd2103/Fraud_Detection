import client from './client';

export const latencyApi = {
  fetchLatencyStats: () => client.get('/latency/stats'),
};

export default latencyApi;

