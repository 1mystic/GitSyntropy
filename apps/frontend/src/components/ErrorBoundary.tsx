import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallbackMessage?: string;
  onRetry?: () => void;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  private retry = () => {
    this.setState({ hasError: false, error: undefined });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[240px] gap-4 p-8 glass-panel rounded-none text-center m-4">
          <span className="material-symbols-outlined text-4xl text-red-400">error_outline</span>
          <div>
            <h3 className="font-bold text-white mb-1">
              {this.props.fallbackMessage ?? "Something went wrong"}
            </h3>
            <p className="text-sm text-gray-400 max-w-sm">
              {this.state.error?.message ?? "An unexpected error occurred rendering this section."}
            </p>
          </div>
          <button
            onClick={this.retry}
            className="px-4 py-2 rounded-lg border border-white/20 text-sm text-gray-300 hover:bg-white/5 hover:text-white transition-colors flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">refresh</span>
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
