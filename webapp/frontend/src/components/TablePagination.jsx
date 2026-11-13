import React from 'react';

export default function TablePagination({
  page,
  setPage,
  limit,
  setLimit,
  totalRecords,
  unit = 'records',
}) {
  const totalPages = Math.max(1, Math.ceil(totalRecords / limit));

  return (
    <div style={{
      padding: '0.75rem 1.25rem',
      borderTop: '1px solid #e4e4e7',
      backgroundColor: '#fafafa',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      flexWrap: 'wrap',
      gap: '0.75rem',
      fontSize: '0.8125rem',
      color: '#71717a',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span>Rows per page:</span>
        <select
          value={limit}
          onChange={(e) => {
            setLimit(Number(e.target.value));
            setPage(1);
          }}
          style={{
            height: '28px',
            padding: '0 0.4rem',
            fontSize: '0.75rem',
            borderRadius: '4px',
            border: '1px solid #e4e4e7',
            backgroundColor: '#ffffff',
            outline: 'none',
          }}
        >
          <option value={20}>20</option>
          <option value={50}>50 (Default)</option>
          <option value={100}>100</option>
          <option value={200}>200</option>
        </select>
        <span style={{ marginLeft: '0.5rem' }}>
          Showing {totalRecords === 0 ? 0 : (page - 1) * limit + 1} - {Math.min(page * limit, totalRecords)} of {totalRecords} {unit}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <button
          onClick={() => setPage(1)}
          disabled={page <= 1}
          className="btn-shadcn btn-secondary"
          style={{ height: '28px', padding: '0 0.5rem', fontSize: '0.75rem' }}
        >
          First
        </button>
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          className="btn-shadcn btn-secondary"
          style={{ height: '28px', padding: '0 0.5rem', fontSize: '0.75rem' }}
        >
          ‹ Prev
        </button>
        <span style={{ fontWeight: 600, color: '#09090b', padding: '0 0.35rem' }}>
          Page {page} / {totalPages}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages}
          className="btn-shadcn btn-secondary"
          style={{ height: '28px', padding: '0 0.5rem', fontSize: '0.75rem' }}
        >
          Next ›
        </button>
        <button
          onClick={() => setPage(totalPages)}
          disabled={page >= totalPages}
          className="btn-shadcn btn-secondary"
          style={{ height: '28px', padding: '0 0.5rem', fontSize: '0.75rem' }}
        >
          Last
        </button>
      </div>
    </div>
  );
}

