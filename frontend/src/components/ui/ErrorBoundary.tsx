import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  title?: string;
  sectionName?: string;
  compact?: boolean;
  fallback?: ReactNode | ((error: Error, retry: () => void) => ReactNode);
  onRetry?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const section = this.props.sectionName || this.props.title || 'Component';
    console.error(`[ErrorBoundary] Caught error in ${section}:`, error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onRetry) {
      this.props.onRetry();
    }
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (typeof this.props.fallback === 'function') {
        return this.props.fallback(this.state.error || new Error('Unknown error'), this.handleRetry);
      }
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { compact, title, sectionName } = this.props;
      const displayTitle = title || (sectionName ? `Error in ${sectionName}` : 'Something went wrong');
      const errorMessage =
        this.state.error?.message || 'An unexpected rendering error occurred. Please try again.';

      if (compact) {
        return (
          <div className="p-4 rounded-card bg-rose-500/10 border border-rose-500/30 text-center space-y-2 h-full flex flex-col items-center justify-center min-h-[140px]">
            <div className="w-8 h-8 rounded-full bg-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-center shrink-0">
              <AlertCircle className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-rose-700 dark:text-rose-300">
                {displayTitle}
              </h4>
              <p className="text-[11px] text-rose-600/80 dark:text-rose-400/80 mt-0.5 line-clamp-2 max-w-xs">
                {errorMessage}
              </p>
            </div>
            <button
              type="button"
              onClick={this.handleRetry}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-helios-accent-blue text-white text-[11px] font-semibold hover:bg-blue-600 transition shadow-sm"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          </div>
        );
      }

      return (
        <div className="p-8 rounded-card bg-rose-500/10 border border-rose-500/30 text-center space-y-4 my-4 max-w-4xl mx-auto">
          <div className="w-12 h-12 mx-auto rounded-full bg-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-center">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-rose-700 dark:text-rose-300">
              {displayTitle}
            </h3>
            <p className="text-xs text-rose-600/80 dark:text-rose-400/80 mt-1 max-w-md mx-auto">
              {errorMessage}
            </p>
          </div>
          <button
            type="button"
            onClick={this.handleRetry}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-control bg-helios-accent-blue text-white text-xs font-semibold hover:bg-blue-600 transition shadow-sm"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Retry</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
