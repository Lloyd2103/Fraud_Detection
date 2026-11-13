import client from './client';

export const authApi = {
  login: (formData) =>
    client.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),

  logout: () => client.post('/auth/logout', {}),

  getMe: (token) => {
    const config = token ? { headers: { Authorization: `Bearer ${token}` } } : {};
    return client.get('/auth/me', config);
  },

  register: (payload) => client.post('/auth/register', payload),

  forgotPassword: (email) => client.post('/auth/forgot-password', { email }),

  verifyOtp: (payload) => client.post('/auth/verify-otp', payload),

  resetPassword: (payload) => client.post('/auth/reset-password', payload),
};

export default authApi;
