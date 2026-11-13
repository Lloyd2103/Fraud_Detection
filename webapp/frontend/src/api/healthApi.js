import client from './client';

export const healthApi = {
  fetchHealth: () => client.get('/health'),
  fetchPipelineHealth: () => client.get('/health/pipeline'),
};

export default healthApi;

