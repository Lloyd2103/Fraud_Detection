import client from './client';

export const modelApi = {
  fetchModelPerformance: () => client.get('/audit/model-performance'),
  fetchModelRegistry: () => client.get('/audit/model-registry'),
  registerModel: (payload) => client.post('/audit/model-registry', payload),
};

export default modelApi;

