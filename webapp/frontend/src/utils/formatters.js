/**
 * Format ISO timestamp to Vietnam Time (Asia/Ho_Chi_Minh)
 * Output: HH:mm:ss dd/MM/yyyy
 */
export function formatVietnamTime(iso) {
  if (!iso) return '-';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    const formatter = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Ho_Chi_Minh',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
    const parts = formatter.formatToParts(d);
    const map = {};
    for (const p of parts) map[p.type] = p.value;
    return `${map.hour}:${map.minute}:${map.second} ${map.day}/${map.month}/${map.year}`;
  } catch (e) {
    return String(iso);
  }
}

