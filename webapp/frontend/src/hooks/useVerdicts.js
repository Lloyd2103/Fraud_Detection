import { useState, useCallback } from 'react';
import { verdictsApi } from '../api';

export function useVerdicts() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getInspected = useCallback(async (options) => {
    setLoading(true);
    setError(null);
    try {
      const res = await verdictsApi.fetchInspectedAlerts(options);
      return res.data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getStats = useCallback(async (params) => {
    const res = await verdictsApi.fetchVerdictsStats(params);
    return res.data;
  }, []);

  const submitDecision = useCallback(async (transactionId, payload) => {
    const res = await verdictsApi.submitInspection(transactionId, payload);
    return res.data;
  }, []);

  return {
    loading,
    error,
    getInspected,
    getStats,
    submitDecision,
    fetchInspectedAlerts: verdictsApi.fetchInspectedAlerts,
    fetchVerdictsStats: verdictsApi.fetchVerdictsStats,
    submitInspection: verdictsApi.submitInspection,
  };
}

export default useVerdicts;

