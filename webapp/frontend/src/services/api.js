import axios from 'axios';

const API_BASE = '/api';

export const fetchAlerts = (status = 'new', limit = 50) => 
  axios.get(`${API_BASE}/alerts`, { params: { status, limit } });

export const fetchAlertSummary = () =>
  axios.get(`${API_BASE}/alerts/summary`);

export const fetchTransactionDetail = (id) =>
  axios.get(`${API_BASE}/transactions/${id}`);

export const submitInspection = (transactionId, payload) =>
  axios.post(`${API_BASE}/transactions/${transactionId}/decision`, payload);

export const fetchModelPerformance = () =>
  axios.get(`${API_BASE}/audit/model-performance`);

export const fetchTimeTravel = (version) =>
  axios.get(`${API_BASE}/audit/time-travel/${version}`);

export const rerunAuditEvaluation = (version) =>
  axios.post(`${API_BASE}/audit/rerun-eval/${version}`);

export const fetchLatencyStats = () =>
  axios.get(`${API_BASE}/latency/stats`);