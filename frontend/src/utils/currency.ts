/**
 * Shared Indian Currency (INR), Number, and Date/Time Formatting Utilities.
 * Locale: en-IN, TimeZone: Asia/Kolkata (IST).
 */

const inrFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * Format numeric amount into standard Indian Rupee string: ₹1,23,456.00
 */
export function formatINR(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') return '₹0.00';
  const val = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(val)) return '₹0.00';
  // Remove possible spaces added by some platform Intl implementations
  return inrFormatter.format(val).replace(/\s+/g, '');
}

/**
 * Format numeric amount with compact Indian units (L for Lakhs, Cr for Crores).
 * Below 1 Lakh, returns the plain formatted value (formatINR).
 * Examples:
 *   15000000 -> ₹1.5Cr
 *   13000000 -> ₹1.3Cr
 *   250000   -> ₹2.5L
 *   420000   -> ₹4.2L
 *   85000    -> ₹85,000.00
 */
export function formatINRCompact(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') return '₹0';
  const val = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(val)) return '₹0';

  const sign = val < 0 ? '-' : '';
  const abs = Math.abs(val);

  if (abs >= 10000000) {
    const cr = abs / 10000000;
    const formatted = cr % 1 === 0 ? cr.toFixed(0) : parseFloat(cr.toFixed(2)).toString();
    return `${sign}₹${formatted}Cr`;
  }

  if (abs >= 100000) {
    const l = abs / 100000;
    const formatted = l % 1 === 0 ? l.toFixed(0) : parseFloat(l.toFixed(2)).toString();
    return `${sign}₹${formatted}L`;
  }

  const rounded = Math.round(abs);
  const formatted = new Intl.NumberFormat('en-IN').format(rounded);
  return `${sign}₹${formatted}`;
}

/**
 * Format count numbers with Indian digit grouping: 1,23,456
 */
export function formatCountIN(n: number | string | null | undefined): string {
  if (n === null || n === undefined || n === '') return '0';
  const val = typeof n === 'string' ? parseInt(n, 10) : n;
  if (isNaN(val)) return '0';
  return new Intl.NumberFormat('en-IN').format(val);
}

/**
 * Format ISO or UTC date string into Indian convention: DD/MM/YYYY in IST.
 */
export function formatDateIN(dateVal: string | Date | null | undefined): string {
  if (!dateVal) return '';
  try {
    const d = typeof dateVal === 'string' ? new Date(dateVal) : dateVal;
    if (isNaN(d.getTime())) return String(dateVal);
    return new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(d);
  } catch {
    return String(dateVal);
  }
}

/**
 * Format ISO or UTC date-time string into Indian convention: DD/MM/YYYY, hh:mm A in IST.
 */
export function formatDateTimeIN(dateVal: string | Date | null | undefined): string {
  if (!dateVal) return '';
  try {
    const d = typeof dateVal === 'string' ? new Date(dateVal) : dateVal;
    if (isNaN(d.getTime())) return String(dateVal);
    return new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    }).format(d);
  } catch {
    return String(dateVal);
  }
}
