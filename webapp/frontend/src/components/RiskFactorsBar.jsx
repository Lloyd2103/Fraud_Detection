import React from 'react';

export default function RiskFactorsBar({ factors = [] }) {
  if (!factors || !factors.length) {
    return (
      <div style={{ marginTop: '1rem', color: '#94a3b8', fontSize: '0.85rem' }}>
        Chưa có yếu tố rủi ro ghi nhận.
      </div>
    );
  }

  return (
    <div style={{ marginTop: '1rem' }}>
      <h4 style={{ fontSize: '0.95rem', marginBottom: '0.75rem', color: '#fff' }}>
        🚨 Top 3 Yếu Tố Rủi Ro Đóng Góp (Giải Thích Mô Hình GBT)
      </h4>
      {factors.map((f, i) => {
        const factorName = f.name || f.ten || f.feature_name || `Yếu tố ${i + 1}`;
        const factorWeight = (f.weight !== undefined ? f.weight : (f.dong_gop !== undefined ? f.dong_gop : (f.contribution !== undefined ? f.contribution : 0.3)));
        const weightPct = Math.round(factorWeight * 100);
        const severity = f.severity || (factorWeight >= 0.4 ? 'CRITICAL' : 'NORMAL');
        const factorVal = f.value || f.gia_tri || '';
        const factorDesc = f.description || f.mo_ta || '';

        return (
          <div key={i} style={{ marginBottom: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.3rem' }}>
              <span style={{ color: '#fff', fontWeight: 500 }}>{factorName}</span>
              <span style={{ color: '#ef4444', fontWeight: 700 }}>{weightPct}% đóng góp</span>
            </div>
            <div style={{ width: '100%', height: '8px', background: '#1e293b', borderRadius: '9999px', overflow: 'hidden' }}>
              <div 
                style={{ 
                  width: `${Math.min(100, Math.max(0, weightPct))}%`, 
                  height: '100%', 
                  background: severity === 'CRITICAL' ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #3b82f6, #f59e0b)',
                  borderRadius: '9999px'
                }}
              />
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
              {factorDesc} {factorVal && `• Giá trị: `}<span style={{ color: '#cbd5e1' }}>{factorVal}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
