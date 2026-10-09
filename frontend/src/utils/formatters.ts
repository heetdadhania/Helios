/**
 * Utility functions for date and string formatting in Helios dashboards.
 */

/**
 * Formats an ISO date string (e.g. "2018-03-14" or "2018-03-14T00:00:00")
 * into a human-readable string like "14 Mar 2018".
 * Returns null if input is null or undefined.
 */
export const formatDateAsOf = (dateStr: string | null | undefined): string | null => {
  if (!dateStr) return null;
  const trimmed = dateStr.trim();
  if (!trimmed) return null;

  try {
    const match = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
      const year = parseInt(match[1], 10);
      const month = parseInt(match[2], 10) - 1;
      const day = parseInt(match[3], 10);
      const dateObj = new Date(Date.UTC(year, month, day));
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return `${dateObj.getUTCDate()} ${monthNames[dateObj.getUTCMonth()]} ${dateObj.getUTCFullYear()}`;
    }

    const d = new Date(trimmed);
    if (isNaN(d.getTime())) return trimmed;
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${d.getUTCDate()} ${monthNames[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  } catch {
    return trimmed;
  }
};
