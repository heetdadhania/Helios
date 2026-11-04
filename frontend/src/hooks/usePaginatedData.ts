import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { PaginatedResponse } from '@/types/pagination';

export interface UsePaginatedDataOptions<T, F extends Record<string, any> = Record<string, any>> {
  fetchFn: (params: { page: number; pageSize: number } & F) => Promise<PaginatedResponse<T> | T[]>;
  filters?: F;
  pageSize?: number;
  enabled?: boolean;
}

export interface UsePaginatedDataReturn<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  isLoading: boolean;
  error: string | null;
  setPage: (newPage: number) => void;
  refetch: () => Promise<void>;
  setData: React.Dispatch<React.SetStateAction<T[]>>;
}

export function usePaginatedData<T, F extends Record<string, any> = Record<string, any>>({
  fetchFn,
  filters,
  pageSize = 20,
  enabled = true,
}: UsePaginatedDataOptions<T, F>): UsePaginatedDataReturn<T> {
  const [searchParams, setSearchParams] = useSearchParams();

  // Read current page from URL query string
  const pageParam = searchParams.get('page');
  const parsedPage = pageParam ? parseInt(pageParam, 10) : 1;
  const page = isNaN(parsedPage) || parsedPage < 1 ? 1 : parsedPage;

  const [data, setData] = useState<T[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Stable refs for fetchFn and filters to prevent infinite re-fetching
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  // Serialize filters to track actual changes
  const serializedFilters = JSON.stringify(filters ?? {});
  const prevFiltersRef = useRef<string>(serializedFilters);
  const isFirstRenderRef = useRef<boolean>(true);

  // Sync page to 1 whenever filters change (after initial mount)
  useEffect(() => {
    if (isFirstRenderRef.current) {
      isFirstRenderRef.current = false;
      return;
    }
    if (prevFiltersRef.current !== serializedFilters) {
      prevFiltersRef.current = serializedFilters;
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (next.get('page') !== '1') {
          next.set('page', '1');
        }
        return next;
      }, { replace: true });
    }
  }, [serializedFilters, setSearchParams]);

  const setPage = useCallback(
    (newPage: number) => {
      const targetPage = Math.max(1, newPage);
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set('page', String(targetPage));
        return next;
      });
    },
    [setSearchParams]
  );

  const fetchData = useCallback(async () => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const activeFilters = (filtersRef.current ?? {}) as F;
      const res = await fetchFnRef.current({
        page,
        pageSize,
        ...activeFilters,
      });

      if (res && typeof res === 'object' && 'items' in res && Array.isArray((res as any).items)) {
        const paginated = res as PaginatedResponse<T>;
        setData(paginated.items);
        setTotal(typeof paginated.total === 'number' ? paginated.total : paginated.items.length);
      } else if (Array.isArray(res)) {
        setData(res);
        setTotal(res.length);
      } else {
        setData([]);
        setTotal(0);
      }
    } catch (err: any) {
      const errorMsg =
        err?.response?.data?.detail ||
        err?.message ||
        'An error occurred while fetching data.';
      setError(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
      setData([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [enabled, page, pageSize, serializedFilters]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return {
    data,
    total,
    page,
    pageSize,
    totalPages,
    isLoading,
    error,
    setPage,
    refetch: fetchData,
    setData,
  };
}
