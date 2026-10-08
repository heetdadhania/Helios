import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export interface PaginationProps {
  currentPage: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export const Pagination: React.FC<PaginationProps> = React.memo(({
  currentPage,
  totalItems,
  pageSize,
  onPageChange,
  className = '',
}) => {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  if (totalItems <= pageSize && currentPage === 1) {
    return null;
  }

  const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(totalItems, currentPage * pageSize);

  // Calculate page numbers to display
  const getPageNumbers = () => {
    const pages: (number | 'ellipsis')[] = [];
    if (totalPages <= 5) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);
      if (currentPage > 3) {
        pages.push('ellipsis');
      }
      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      if (currentPage < totalPages - 2) {
        pages.push('ellipsis');
      }
      pages.push(totalPages);
    }
    return pages;
  };

  return (
    <div
      className={`px-4 py-3 flex items-center justify-between border-t border-helios-border-light dark:border-helios-border-dark bg-black/[0.01] dark:bg-white/[0.01] text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark ${className}`}
    >
      <div className="flex-1 flex justify-between sm:hidden">
        <button
          type="button"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="relative inline-flex items-center px-3 py-1.5 rounded-lg border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-helios-text-primary-light dark:text-helios-text-primary-dark font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
        >
          Previous
        </button>
        <span className="self-center font-medium">
          {currentPage} / {totalPages}
        </span>
        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="relative inline-flex items-center px-3 py-1.5 rounded-lg border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-helios-text-primary-light dark:text-helios-text-primary-dark font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
        >
          Next
        </button>
      </div>

      <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
        <div>
          <p className="text-xs">
            Showing <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">{startItem}</span> to{' '}
            <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">{endItem}</span> of{' '}
            <span className="font-semibold text-helios-text-primary-light dark:text-helios-text-primary-dark">{totalItems}</span> results
          </p>
        </div>
        <div>
          <nav className="relative z-0 inline-flex items-center gap-1 rounded-md shadow-2xs" aria-label="Pagination">
            <button
              type="button"
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="relative inline-flex items-center p-1.5 rounded-lg border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:bg-black/5 dark:hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            {getPageNumbers().map((page, idx) =>
              page === 'ellipsis' ? (
                <span
                  key={`ellipsis-${idx}`}
                  className="px-2 py-1 text-slate-400 dark:text-slate-500"
                >
                  …
                </span>
              ) : (
                <button
                  key={page}
                  type="button"
                  onClick={() => onPageChange(page)}
                  className={`min-w-[28px] h-7 px-2 flex items-center justify-center rounded-lg text-xs font-semibold transition-colors ${
                    currentPage === page
                      ? 'bg-helios-accent-blue text-white shadow-2xs'
                      : 'border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-helios-text-primary-light dark:text-helios-text-primary-dark hover:bg-black/5 dark:hover:bg-white/5'
                  }`}
                >
                  {page}
                </button>
              )
            )}

            <button
              type="button"
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="relative inline-flex items-center p-1.5 rounded-lg border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark hover:bg-black/5 dark:hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </nav>
        </div>
      </div>
    </div>
  );
});

Pagination.displayName = 'Pagination';
