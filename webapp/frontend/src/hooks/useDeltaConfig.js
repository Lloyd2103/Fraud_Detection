import { useState, useCallback } from 'react';
import { deltaConfigApi } from '../api';

export function useDeltaConfig() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getConfig = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await deltaConfigApi.fetchDeltaConfig();
      return res.data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    getConfig,
    fetchDeltaConfig: deltaConfigApi.fetchDeltaConfig,
  };
}

export default useDeltaConfig;

