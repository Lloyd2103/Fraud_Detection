import client from './client';

export const usersApi = {
  getUsers: () => client.get('/auth/users'),
  updateUserRoleStatus: (userId, payload) => client.patch(`/auth/users/${userId}`, payload),
};

export default usersApi;

