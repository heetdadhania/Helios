import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { ArrowDown, ArrowUp } from 'lucide-react';

export interface SortOption {
  value: string;
  label: string;
}

export interface SortControlProps {
  options: SortOption[];
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSortChange?: (sortBy: string, sortOrder: 'asc' | 'desc') => void;
  className?: string;
  defaultSortBy?: string;
  defaultSortOrder?: 'asc' | 'desc';
}

export const SortControl: React.FC<SortControlProps> = ({
  options,
  sortBy,
  sortOrder,
  onSortChange,
  className = '',
  defaultSortOrder = 'asc',
}) => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Read sort_by and sort_order from URL or fallback to props
  const paramSortBy = searchParams.get('sort_by');
  const paramSortOrder = searchParams.get('sort_order') as 'asc' | 'desc' | null;

  const activeSortBy = sortBy !== undefined ? sortBy : (paramSortBy || '');
  const activeSortOrder = sortOrder !== undefined ? sortOrder : (paramSortOrder || defaultSortOrder);

  const handleFieldChange = (newField: string) => {
    const nextSortBy = newField.trim();
    const nextSortOrder = activeSortOrder || 'asc';

    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (nextSortBy) {
        next.set('sort_by', nextSortBy);
        next.set('sort_order', nextSortOrder);
      } else {
        next.delete('sort_by');
        next.delete('sort_order');
      }
      next.set('page', '1');
      return next;
    });

    if (onSortChange) {
      onSortChange(nextSortBy, nextSortOrder);
    }
  };

  const handleToggleDirection = () => {
    const nextSortOrder: 'asc' | 'desc' = activeSortOrder === 'asc' ? 'desc' : 'asc';

    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (activeSortBy) {
        next.set('sort_by', activeSortBy);
        next.set('sort_order', nextSortOrder);
      } else {
        // If no sort_by selected yet, select the first option by default
        const defaultFirst = options.length > 0 ? options[0].value : '';
        if (defaultFirst) {
          next.set('sort_by', defaultFirst);
          next.set('sort_order', nextSortOrder);
        }
      }
      next.set('page', '1');
      return next;
    });

    if (onSortChange) {
      onSortChange(activeSortBy || (options.length > 0 ? options[0].value : ''), nextSortOrder);
    }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <label htmlFor="sort-by-select" className="text-xs font-medium text-helios-text-secondary-light dark:text-helios-text-secondary-dark whitespace-nowrap">
        Sort by:
      </label>
      <select
        id="sort-by-select"
        value={activeSortBy}
        onChange={(e) => handleFieldChange(e.target.value)}
        className="px-3 py-1.5 text-xs rounded-xl bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark focus:outline-none focus:ring-1 focus:ring-helios-accent-blue transition-all cursor-pointer"
        aria-label="Sort by field"
      >
        <option value="">Default</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      <button
        type="button"
        onClick={handleToggleDirection}
        title={activeSortOrder === 'asc' ? 'Sort Ascending (click for Descending)' : 'Sort Descending (click for Ascending)'}
        aria-label={activeSortOrder === 'asc' ? 'Sort ascending' : 'Sort descending'}
        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-helios-border-light dark:border-helios-border-dark bg-helios-card-light dark:bg-helios-card-dark hover:bg-black/5 dark:hover:bg-white/5 text-xs text-helios-text-primary-light dark:text-helios-text-primary-dark font-medium transition-colors cursor-pointer"
      >
        {activeSortOrder === 'asc' ? (
          <>
            <ArrowUp className="w-3.5 h-3.5 text-helios-accent-blue" />
            <span className="hidden sm:inline">Asc</span>
          </>
        ) : (
          <>
            <ArrowDown className="w-3.5 h-3.5 text-helios-accent-blue" />
            <span className="hidden sm:inline">Desc</span>
          </>
        )}
      </button>
    </div>
  );
};

