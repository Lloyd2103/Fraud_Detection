import { useState, useCallback } from 'react';
import { usersApi } from '../api';

export function useUsers() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await usersApi.getUsers();
      return res.data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateRoleStatus = useCallback(async (userId, payload) => {
    const res = await usersApi.updateUserRoleStatus(userId, payload);
    return res.data;
  }, []);

  return {
    loading,
    error,
    getUsers,
    updateRoleStatus,
    fetchUsers: usersApi.getUsers,
    updateUserRoleStatus: usersApi.updateUserRoleStatus,
  };
}

export default useUsers;

