import React, { useEffect } from 'react';
import {
  Activity, CheckCircle2, AlertTriangle, Workflow, Cpu, Server,
  RefreshCw, AlertCircle, Info
} from 'lucide-react';
import { useLatency } from '../../hooks/useLatency';

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
const secStr = (ms) => (isNum(ms) ? `${(ms / 1000).toFixed(2)}s` : '—');
const pctStr = (v) => (isNum(v) ? `${v}%` : '—');

const STATUS_STYLE = {
  HEALTHY:  { color: '#16a34a', bg: '#f0fdf4', border: '#dcfce7', Icon: CheckCircle2, label: 'SLA met' },
  WARNING:  { color: '#d97706', bg: '#fffbeb', border: '#fef3c7', Icon: AlertTriangle, label: 'SLA partially met' },
  CRITICAL: { color: '#dc2626', bg: '#fef2f2', border: '#fee2e2', Icon: AlertCircle, label: 'SLA not met' },
  NO_DATA:  { color: '#71717a', bg: '#fafafa', border: '#e4e4e7', Icon: Info, label: 'No latency data' },
};

const labelStyle = { fontSize: '0.75rem', color: '#71717a', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' };
const bigStyle = { fontSize: '1.75rem', fontWeight: 700, color: '#09090b', marginTop: '0.35rem', letterSpacing: '-0.02em' };
const noteStyle = { fontSize: '0.75rem', color: '#71717a', marginTop: '0.2rem' };

function Badge({ text, color, bg, border }) {
  return (
    <span style={{ fontSize: '0.6875rem', fontWeight: 600, color, backgroundColor: bg, padding: '0.15rem 0.5rem', borderRadius: '4px', border: `1px solid ${border}` }}>
      {text}
    </span>
  );
}

export default function LatencyPage() {
  const { latency, loading, error, refresh } = useLatency();

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading && !latency) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', color: '#71717a' }} />
      </div>
    );
  }

  if (error && !latency) {
    return (
      <div style={{ padding: '1.25rem', borderRadius: '8px', backgroundColor: '#fef2f2', border: '1px solid #fee2e2', color: '#991b1b', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <AlertCircle size={20} />
        <div>
          <div style={{ fontWeight: 600 }}>Failed to load latency metrics</div>
          <div style={{ fontSize: '0.8125rem', marginTop: '0.25rem' }}>{error.message || 'Unknown error occurred'}</div>
        </div>
        <button onClick={refresh} className="btn-shadcn btn-secondary" style={{ marginLeft: 'auto', height: '2rem', padding: '0 0.75rem' }}>
          Retry
        </button>
      </div>
    );
  }

  const status = latency?.status || 'NO_DATA';
  const hasData = status !== 'NO_DATA' && isNum(latency?.total_measured_alerts) && latency.total_measured_alerts > 0;
  const st = STATUS_STYLE[status] || STATUS_STYLE.NO_DATA;
  const StatusIcon = st.Icon;

  const p50 = hasData ? latency.p50_latency_ms : null;
  const p95 = hasData ? latency.p95_latency_ms : null;
  const p99 = hasData ? latency.p99_latency_ms : null;
  const maxMs = hasData ? latency.max_latency_ms : null;
  const total = hasData ? latency.total_measured_alerts : null;
  const rate2 = hasData ? latency.sla_2s_rate : null;
  const rate5 = hasData ? latency.sla_5s_rate : null;

  const p95Pass = isNum(p95) ? p95 < 2000 : null;
  const p99Within5 = isNum(p99) ? p99 <= 5000 : null;
  const rateColor = (v) => (!isNum(v) ? '#71717a' : v >= 95 ? '#16a34a' : '#d97706');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="shadcn-card" style={{ padding: '1.5rem', backgroundColor: '#ffffff' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Activity size={20} style={{ color: st.color }} />
              <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.02em' }}>
                Scoring Latency &amp; SLA Compliance
              </h2>
            </div>
            <p style={{ margin: '0.35rem 0 0', fontSize: '0.8125rem', color: '#71717a', lineHeight: 1.5 }}>
              Measured from Kafka producer timestamp to Spark scoring. Excludes Delta write, CockroachDB sync and WebSocket delivery. Records with latency &gt; 60 s are excluded from these percentiles.
            </p>
            <div style={{ fontSize: '0.72rem', color: '#a1a1aa', marginTop: '0.25rem', fontStyle: 'italic' }}>
              Values above 60 s may reflect a timestamp artifact and are under investigation. This is not the end-to-end latency to the web UI.
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.35rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: st.color, backgroundColor: st.bg, padding: '0.25rem 0.65rem', borderRadius: '6px', border: `1px solid ${st.border}`, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <StatusIcon size={13} />
              {st.label}
            </span>
            {latency?.status_reason && (
              <span style={{ fontSize: '0.72rem', color: '#71717a', maxWidth: '22rem', textAlign: 'right' }}>{latency.status_reason}</span>
            )}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <div style={labelStyle}>P50 Median Latency</div>
          <div style={bigStyle}>{secStr(p50)}</div>
          <div style={noteStyle}>50% of alerts scored within this time</div>
        </div>

        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={labelStyle}>P95 Latency (SLA Target)</span>
            {p95Pass !== null && (
              <Badge text={p95Pass ? 'Within 2s target' : 'Above 2s target'}
                color={p95Pass ? '#16a34a' : '#dc2626'} bg={p95Pass ? '#f0fdf4' : '#fef2f2'} border={p95Pass ? '#dcfce7' : '#fee2e2'} />
            )}
          </div>
          <div style={bigStyle}>{secStr(p95)}</div>
          <div style={noteStyle}>Target: &lt; 2.00s</div>
        </div>

        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={labelStyle}>P99 Tail Latency</span>
            {p99Within5 !== null && (
              <Badge text={p99Within5 ? 'Within 5s limit' : 'Above 5s limit'}
                color={p99Within5 ? '#16a34a' : '#d97706'} bg={p99Within5 ? '#f0fdf4' : '#fffbeb'} border={p99Within5 ? '#dcfce7' : '#fef3c7'} />
            )}
          </div>
          <div style={bigStyle}>{secStr(p99)}</div>
          <div style={noteStyle}>Tail latency for 99th percentile</div>
        </div>

        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <div style={labelStyle}>Samples Measured</div>
          <div style={bigStyle}>{isNum(total) ? total.toLocaleString('en-US') : '—'}</div>
          <div style={noteStyle}>Max latency: {secStr(maxMs)} (valid events &le; 60s)</div>
        </div>
      </div>

      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <h3 style={{ margin: '0 0 0.85rem 0', fontSize: '0.9375rem', fontWeight: 600, color: '#09090b' }}>
          SLA Compliance Breakdown
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          <div style={{ padding: '0.85rem 1rem', backgroundColor: '#fafafa', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>Within 2 s (Scoring SLA Target - Section 2.1)</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: rateColor(rate2), marginTop: '0.25rem' }}>{pctStr(rate2)}</div>
            <div style={{ fontSize: '0.72rem', color: '#a1a1aa', marginTop: '0.2rem' }}>Team threshold &ge; 95% (not specified in the assignment)</div>
          </div>
          <div style={{ padding: '0.85rem 1rem', backgroundColor: '#fafafa', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>Within 5 s (Section 2.8 limit; scoring stage only)</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: rateColor(rate5), marginTop: '0.25rem' }}>{pctStr(rate5)}</div>
            <div style={{ fontSize: '0.72rem', color: '#a1a1aa', marginTop: '0.2rem' }}>Team threshold &ge; 95% (not specified in the assignment)</div>
          </div>
        </div>
      </div>

      <div className="shadcn-card" style={{ padding: '1.5rem' }}>
        <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9375rem', fontWeight: 600, color: '#09090b' }}>
          Pipeline Stages (per-stage timing not measured)
        </h3>
        <p style={{ margin: '0 0 1rem 0', fontSize: '0.8125rem', color: '#71717a', fontStyle: 'italic' }}>
          Per-stage breakdown is not measured. Only the producer-to-scoring latency is recorded.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {[
            { Icon: Workflow, title: 'Spark Micro-batch Trigger & Kafka Ingestion', text: "Polls raw events from Kafka topic 'transactions' via Spark Streaming consumer." },
            { Icon: Cpu, title: 'GBT Model Inference & Feature Assembly', text: 'Assembles feature vectors and runs Spark MLlib GBTClassifier to predict risk_score.' },
            { Icon: Server, title: 'Kafka Alert Sink & Gold Delta Lake Append', text: "Emits high-risk alerts to Kafka topic 'alerts' and appends scored batch to Delta Lake." },
          ].map(({ Icon, title, text }) => (
            <div key={title} style={{ padding: '0.75rem 1rem', backgroundColor: '#fafafa', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
              <div style={{ fontWeight: 600, color: '#09090b', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8125rem' }}>
                <Icon size={14} /> {title}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.2rem' }}>{text}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
