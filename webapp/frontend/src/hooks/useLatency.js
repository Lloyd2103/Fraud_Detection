import { useState, useCallback } from 'react';
import { latencyApi } from '../api';

export function useLatency() {
  const [latency, setLatency] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Giữ nguyên hợp đồng cũ: trả về dữ liệu (AlertQueuePage đang dùng hàm này).
  const getLatencyStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await latencyApi.fetchLatencyStats();
      setLatency(res.data);
      return res.data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Dùng cho trang Latency: không ném lỗi, lỗi nằm trong state `error`.
  const refresh = useCallback(async () => {
    try {
      await getLatencyStats();
    } catch {
      /* error đã được lưu trong state */
    }
  }, [getLatencyStats]);

  return {
    latency,
    loading,
    error,
    refresh,
    getLatencyStats,
    fetchLatencyStats: latencyApi.fetchLatencyStats,
  };
}

export default useLatency;
