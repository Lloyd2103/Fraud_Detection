// Number formatting shared by the Fraud Summary page and its matrix table (en-US everywhere).
// Amounts carry no currency label: the source data does not specify the currency.

export const fmt = (n) => Number(n || 0).toLocaleString('en-US');

export const fmtAmount = (n) => {
  const v = Number(n || 0);
  if (v >= 1e12) return `${(v / 1e12).toFixed(2)} T`;
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)} B`;
  return `${(v / 1e6).toFixed(2)} M`;
};

export const fmtPct = (n) => {
  const num = Number(n || 0);
  if (num > 0 && num < 0.1) return `${num.toFixed(4)}%`;
  return `${num.toFixed(2)}%`;
};
