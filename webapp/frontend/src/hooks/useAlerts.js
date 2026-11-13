import { useState, useCallback } from 'react';
import { alertsApi } from '../api';

export function useAlerts() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getAlerts = useCallback(async (options) => {
    setLoading(true);
    setError(null);
    try {
      const res = await alertsApi.fetchAlerts(options);
      return res.data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getSummary = useCallback(async (inspectorId) => {
    try {
      const res = await alertsApi.fetchAlertSummary(inspectorId);
      return res.data;
    } catch (err) {
      console.error('Failed to fetch summary:', err);
      return null;
    }
  }, []);

  const getCdf = useCallback(async (startingVersion) => {
    const res = await alertsApi.fetchCdfAlerts(startingVersion);
    return res.data;
  }, []);

  return {
    loading,
    error,
    getAlerts,
    getSummary,
    getCdf,
    fetchAlerts: alertsApi.fetchAlerts,
    fetchAlertSummary: alertsApi.fetchAlertSummary,
    fetchCdfAlerts: alertsApi.fetchCdfAlerts,
  };
}

export default useAlerts;

