import { useState, useCallback } from 'react';
import { modelApi } from '../api';

export function useModelGovernance() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getPerformance = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await modelApi.fetchModelPerformance();
      return res.data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getRegistry = useCallback(async () => {
    const res = await modelApi.fetchModelRegistry();
    return res.data;
  }, []);

  const registerModel = useCallback(async (payload) => {
    const res = await modelApi.registerModel(payload);
    return res.data;
  }, []);

  return {
    loading,
    error,
    getPerformance,
    getRegistry,
    registerModel,
    fetchModelPerformance: modelApi.fetchModelPerformance,
    fetchModelRegistry: modelApi.fetchModelRegistry,
  };
}

export default useModelGovernance;

