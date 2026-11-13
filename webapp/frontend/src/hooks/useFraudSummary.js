import { useState, useCallback } from 'react';
import { fraudSummaryApi } from '../api';

export function useFraudSummary() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getSummary = useCallback(async (params = {}) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fraudSummaryApi.fetchFraudSummary(params);
      return res.data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getOverall = useCallback(async () => {
    const res = await fraudSummaryApi.fetchFraudSummaryOverall();
    return res.data;
  }, []);

  const recalculate = useCallback(async () => {
    const res = await fraudSummaryApi.recalculateFraudSummary();
    return res.data;
  }, []);

  return {
    loading,
    error,
    getSummary,
    getOverall,
    recalculate,
    fetchFraudSummary: fraudSummaryApi.fetchFraudSummary,
    fetchFraudSummaryOverall: fraudSummaryApi.fetchFraudSummaryOverall,
    recalculateFraudSummary: fraudSummaryApi.recalculateFraudSummary,
  };
}

export default useFraudSummary;

