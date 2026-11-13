import client from './client';

export const deltaConfigApi = {
  fetchDeltaConfig: () => client.get('/delta/config'),
};

export default deltaConfigApi;

