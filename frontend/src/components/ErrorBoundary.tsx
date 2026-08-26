import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
          <div className="glass-panel p-8 max-w-lg w-full text-center space-y-4 border-rose-500/30 shadow-[0_0_50px_rgba(244,63,94,0.1)]">
            <div className="w-16 h-16 bg-rose-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="w-8 h-8 text-rose-400" />
            </div>
            <h1 className="text-xl font-bold text-white">Frontend Crash Detected</h1>
            <p className="text-sm text-slate-300 bg-slate-900 p-4 rounded text-left font-mono overflow-auto max-h-48 border border-white/5">
              {this.state.error?.message || 'An unexpected error occurred in the React tree.'}
            </p>
            <button
              onClick={this.handleReset}
              className="mt-6 w-full btn-primary bg-indigo-600 hover:bg-indigo-500"
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
