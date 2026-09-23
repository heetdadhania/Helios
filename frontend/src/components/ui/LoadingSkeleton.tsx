import React from 'react';

export type SkeletonVariant =
  | 'text'
  | 'circular'
  | 'rectangular'
  | 'card'
  | 'table-row'
  | 'chart';

export interface LoadingSkeletonProps {
  variant?: SkeletonVariant;
  className?: string;
  count?: number;
  width?: string | number;
  height?: string | number;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  variant = 'text',
  className = '',
  count = 1,
  width,
  height,
}) => {
  const baseStyle: React.CSSProperties = {
    width: width,
    height: height,
  };

  const renderSingle = (index: number) => {
    switch (variant) {
      case 'circular':
        return (
          <div
            key={index}
            style={baseStyle}
            className={`rounded-full bg-neutral-200 dark:bg-neutral-800/80 animate-pulse ${
              !width && !height ? 'w-10 h-10' : ''
            } ${className}`}
          />
        );

      case 'card':
        return (
          <div
            key={index}
            style={baseStyle}
            className={`p-5 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark shadow-sm space-y-4 ${className}`}
          >
            <div className="flex items-center justify-between">
              <div className="h-4 w-32 bg-neutral-200 dark:bg-neutral-800 animate-pulse rounded" />
              <div className="h-6 w-6 rounded-full bg-neutral-200 dark:bg-neutral-800 animate-pulse" />
            </div>
            <div className="h-8 w-24 bg-neutral-200 dark:bg-neutral-800 animate-pulse rounded" />
            <div className="h-3 w-48 bg-neutral-200 dark:bg-neutral-800/60 animate-pulse rounded" />
          </div>
        );

      case 'table-row':
        return (
          <tr key={index} className={`border-b border-helios-border-light dark:border-helios-border-dark ${className}`}>
            <td className="py-3 px-4">
              <div className="h-4 w-24 bg-neutral-200 dark:bg-neutral-800 animate-pulse rounded" />
            </td>
            <td className="py-3 px-4">
              <div className="h-4 w-36 bg-neutral-200 dark:bg-neutral-800 animate-pulse rounded" />
            </td>
            <td className="py-3 px-4">
              <div className="h-4 w-20 bg-neutral-200 dark:bg-neutral-800 animate-pulse rounded" />
            </td>
            <td className="py-3 px-4 text-right">
              <div className="h-4 w-16 bg-neutral-200 dark:bg-neutral-800 animate-pulse rounded ml-auto" />
            </td>
          </tr>
        );

      case 'chart':
        return (
          <div
            key={index}
            style={baseStyle}
            className={`p-5 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark space-y-4 ${className}`}
          >
            <div className="h-4 w-40 bg-neutral-200 dark:bg-neutral-800 animate-pulse rounded" />
            <div className="h-48 w-full flex items-end gap-3 pt-6">
              {[40, 75, 55, 90, 65, 80, 45, 95].map((pct, barIdx) => (
                <div
                  key={barIdx}
                  style={{ height: `${pct}%` }}
                  className="flex-1 bg-neutral-200 dark:bg-neutral-800/60 animate-pulse rounded-t"
                />
              ))}
            </div>
          </div>
        );

      case 'rectangular':
        return (
          <div
            key={index}
            style={baseStyle}
            className={`rounded-control bg-neutral-200 dark:bg-neutral-800 animate-pulse ${
              !height ? 'h-24' : ''
            } ${className}`}
          />
        );

      case 'text':
      default:
        return (
          <div
            key={index}
            style={baseStyle}
            className={`h-4 bg-neutral-200 dark:bg-neutral-800 animate-pulse rounded ${
              !width ? 'w-full' : ''
            } ${className}`}
          />
        );
    }
  };

  if (count <= 1) {
    return renderSingle(0);
  }

  return (
    <>
      {Array.from({ length: count }, (_, idx) => renderSingle(idx))}
    </>
  );
};
