import { useState, useCallback } from 'react';
import { auditApi } from '../api';

export function useAudit() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getTimeTravel = useCallback(async (version, config) => {
    setLoading(true);
    setError(null);
    try {
      const res = await auditApi.fetchTimeTravel(version, config);
      return res.data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getCommits = useCallback(async (limit = 145) => {
    const res = await auditApi.fetchDeltaCommits(limit);
    return res.data;
  }, []);

  const rerunEval = useCallback(async (version, params) => {
    const res = await auditApi.rerunAuditEvaluation(version, params);
    return res.data;
  }, []);

  const getTrail = useCallback(async (limit = 50) => {
    const res = await auditApi.fetchAuditTrail(limit);
    return res.data;
  }, []);

  return {
    loading,
    error,
    getTimeTravel,
    getCommits,
    rerunEval,
    getTrail,
    fetchTimeTravel: auditApi.fetchTimeTravel,
    fetchDeltaCommits: auditApi.fetchDeltaCommits,
    rerunAuditEvaluation: auditApi.rerunAuditEvaluation,
    fetchAuditTrail: auditApi.fetchAuditTrail,
  };
}

export default useAudit;

