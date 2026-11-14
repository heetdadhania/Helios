/**
 * frontend/src/utils/unwrapList.ts
 *
 * Universal adapter for handling both unpaginated (plain array) and
 * server-side paginated ({ items: T[], total: number, page?: number, pageSize?: number })
 * API list responses across the entire application.
 *
 * Guarantees that items is always a valid JavaScript Array, preventing
 * uncaught `.map is not a function`, `.filter is not a function`, etc.
 */

export interface UnwrappedList<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

/**
 * Normalizes an API response into a standard UnwrappedList structure.
 * Handles plain arrays, paginated envelopes, nested data properties, and nil/malformed inputs.
 */
export function unwrapList<T = any>(response: any): UnwrappedList<T> {
  if (response === null || response === undefined) {
    return { items: [], total: 0, page: 1, pageSize: 0 };
  }

  // Case 1: Direct Array
  if (Array.isArray(response)) {
    return {
      items: response,
      total: response.length,
      page: 1,
      pageSize: response.length,
    };
  }

  // Case 2: Object containing an array property (items, data, results, records)
  if (typeof response === 'object') {
    let items: T[] = [];
    if (Array.isArray(response.items)) {
      items = response.items;
    } else if (Array.isArray(response.data)) {
      items = response.data;
    } else if (Array.isArray(response.results)) {
      items = response.results;
    } else if (Array.isArray(response.records)) {
      items = response.records;
    } else if (Array.isArray(response.rows)) {
      items = response.rows;
    }

    const total =
      typeof response.total === 'number'
        ? response.total
        : typeof response.total_count === 'number'
        ? response.total_count
        : typeof response.count === 'number'
        ? response.count
        : items.length;

    const page =
      typeof response.page === 'number'
        ? response.page
        : typeof response.current_page === 'number'
        ? response.current_page
        : 1;

    const pageSize =
      typeof response.page_size === 'number'
        ? response.page_size
        : typeof response.pageSize === 'number'
        ? response.pageSize
        : items.length;

    return { items, total, page, pageSize };
  }

  // Fallback for non-array / non-object primitive
  return { items: [], total: 0, page: 1, pageSize: 0 };
}

/**
 * Convenience helper that extracts and returns strictly the items array.
 * Ideal for direct inline chaining: unwrapItems(response).map(...)
 */
export function unwrapItems<T = any>(response: any): T[] {
  return unwrapList<T>(response).items;
}
