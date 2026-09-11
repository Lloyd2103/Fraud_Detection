import axios from 'axios';

const API_BASE = '/api';

// Hàng đợi cảnh báo: GET /api/canhbao?trang_thai=moi (DeTai2.pdf Section 2.8)
export const fetchAlerts = (status = 'new', limit = 50) => {
  const trang_thai = status === 'new' ? 'moi' : (status === 'processed' ? 'da_xu_ly' : 'tat_ca');
  return axios.get(`${API_BASE}/canhbao`, { 
    params: { 
      trang_thai, 
      status, 
      gioi_han: limit, 
      limit 
    } 
  });
};

// Tổng quan cảnh báo: GET /api/canhbao/tong-quan
export const fetchAlertSummary = () =>
  axios.get(`${API_BASE}/canhbao/tong-quan`);

// Chi tiết giao dịch: GET /api/giaodich/{id} (DeTai2.pdf Section 2.8)
export const fetchTransactionDetail = (id) =>
  axios.get(`${API_BASE}/giaodich/${id}`);

// Kết luận thẩm định: POST /api/giaodich/{id}/ket-luan (DeTai2.pdf Section 2.8)
export const submitInspection = (transactionId, payload) =>
  axios.post(`${API_BASE}/giaodich/${transactionId}/ket-luan`, payload);

// Bảng điều khiển mô hình: GET /api/mo-hinh/hieunang (DeTai2.pdf Section 2.8)
export const fetchModelPerformance = () =>
  axios.get(`${API_BASE}/mo-hinh/hieunang`);

// Kiểm toán / Time travel: GET /api/kiemtoan/{phien_ban} (DeTai2.pdf Section 2.8)
export const fetchTimeTravel = (version) =>
  axios.get(`${API_BASE}/kiemtoan/${version}`);

// Chạy lại đánh giá kiểm toán: POST /api/kiemtoan/{phien_ban}/danh-gia-lai
export const rerunAuditEvaluation = (version) =>
  axios.post(`${API_BASE}/kiemtoan/${version}/danh-gia-lai`);

// Thống kê độ trễ: GET /api/do-tre/thong-ke (< 5s SLA per DeTai2.pdf)
export const fetchLatencyStats = () =>
  axios.get(`${API_BASE}/do-tre/thong-ke`);

// Đọc Change Data Feed: GET /api/canhbao/cdf (DeTai2.pdf Section 2.7)
export const fetchCdfAlerts = (startingVersion = 0) =>
  axios.get(`${API_BASE}/canhbao/cdf`, { 
    params: { 
      starting_version: startingVersion, 
      phien_ban_bat_dau: startingVersion 
    } 
  });