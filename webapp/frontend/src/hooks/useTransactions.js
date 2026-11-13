import { useState, useCallback } from 'react';
import { transactionsApi } from '../api';

export function useTransactions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getDetail = useCallback(async (id) => {
    setLoading(true);
    setError(null);
    try {
      const res = await transactionsApi.fetchTransactionDetail(id);
      return res.data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateDetail = useCallback(async (transactionId, payload) => {
    const res = await transactionsApi.updateTransaction(transactionId, payload);
    return res.data;
  }, []);

  return {
    loading,
    error,
    getDetail,
    updateDetail,
    fetchTransactionDetail: transactionsApi.fetchTransactionDetail,
    updateTransaction: transactionsApi.updateTransaction,
  };
}

export default useTransactions;

