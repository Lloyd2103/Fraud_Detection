import React from 'react';

export default function AlertTable({ alerts = [], onSelectTx }) {
  if (!alerts.length) {
    return (
      <div style={{ textAlign: 'center', padding: '2.5rem', color: '#94a3b8' }}>
        Chưa có giao dịch cảnh báo nào trong hàng đợi (Hệ thống chờ nhận dữ liệu từ Kafka / Delta Lake).
      </div>
    );
  }

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
        <thead>
          <tr style={{ background: 'rgba(30, 41, 59, 0.5)', color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase' }}>
            <th style={{ padding: '0.75rem 1rem' }}>Mã GD (Tx ID)</th>
            <th style={{ padding: '0.75rem 1rem' }}>Thời điểm</th>
            <th style={{ padding: '0.75rem 1rem' }}>Nguồn ➔ Đích</th>
            <th style={{ padding: '0.75rem 1rem' }}>Kênh / Loại</th>
            <th style={{ padding: '0.75rem 1rem' }}>Số tiền (VND)</th>
            <th style={{ padding: '0.75rem 1rem' }}>Điểm rủi ro</th>
            <th style={{ padding: '0.75rem 1rem' }}>Trạng thái</th>
            <th style={{ padding: '0.75rem 1rem' }}>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((tx, idx) => {
            const txId = tx.ma_giao_dich || tx.transaction_id || `TX_${idx}`;
            const timeStr = tx.thoi_diem || tx.timestamp || '';
            const srcAcc = tx.tai_khoan_nguon || tx.source_account || 'N/A';
            const dstAcc = tx.tai_khoan_dich || tx.dest_account || 'N/A';
            const channel = tx.kenh || tx.channel || 'ONLINE';
            const transType = tx.loai || tx.trans_type || '';
            const amt = tx.so_tien !== undefined ? tx.so_tien : (tx.amount !== undefined ? tx.amount : 0);
            const score = parseFloat(tx.diem_rui_ro !== undefined ? tx.diem_rui_ro : (tx.risk_score || 0));
            const scorePct = (score * 100).toFixed(1);
            
            const rawStatus = tx.trang_thai_tham_dinh || tx.inspection_status || tx.audit_status || 'PENDING';
            const isProcessed = rawStatus === 'PROCESSED' || rawStatus === 'da_xu_ly' || rawStatus === 'INSPECTED';
            const formattedAmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(amt);

            return (
              <tr key={txId} style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <td style={{ padding: '0.75rem 1rem', fontFamily: 'monospace', fontWeight: 600, color: '#fff' }}>
                  {txId}
                </td>
                <td style={{ padding: '0.75rem 1rem', fontSize: '0.82rem', color: '#94a3b8' }}>
                  {timeStr}
                </td>
                <td style={{ padding: '0.75rem 1rem', fontSize: '0.82rem', fontFamily: 'monospace' }}>
                  {srcAcc} ➔ {dstAcc}
                </td>
                <td style={{ padding: '0.75rem 1rem' }}>
                  <span style={{ background: '#1e293b', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem' }}>
                    {channel} {transType && `• ${transType}`}
                  </span>
                </td>
                <td style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>{formattedAmt}</td>
                <td style={{ padding: '0.75rem 1rem' }}>
                  <span style={{ 
                    padding: '0.2rem 0.6rem', 
                    borderRadius: '9999px', 
                    fontWeight: 700, 
                    fontSize: '0.78rem',
                    background: score >= 0.8 ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)',
                    color: score >= 0.8 ? '#fca5a5' : '#fcd34d'
                  }}>
                    {scorePct}%
                  </span>
                </td>
                <td style={{ padding: '0.75rem 1rem' }}>
                  {isProcessed ? (
                    <span style={{ color: '#10b981', fontSize: '0.78rem' }}>✓ Đã thẩm định</span>
                  ) : (
                    <span style={{ color: '#ef4444', fontSize: '0.78rem' }}>Chờ xử lý</span>
                  )}
                </td>
                <td style={{ padding: '0.75rem 1rem' }}>
                  <button 
                    onClick={() => onSelectTx(txId)}
                    style={{ 
                      background: '#3b82f6', 
                      color: '#fff', 
                      border: 'none', 
                      padding: '0.35rem 0.75rem', 
                      borderRadius: '6px', 
                      cursor: 'pointer',
                      fontSize: '0.8rem'
                    }}
                  >
                    🔍 Thẩm định
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
