/**
 * Global ErrorBoundary
 * 阻止 React 渲染错误导致白屏。
 * 生产环境：不暴露 stack trace / 内部路径
 * 开发环境：保留 console.error + 显示原始 message
 */
import { Component, ReactNode, ErrorInfo } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      errorMessage: error?.message || "Unknown error",
    };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // 仅开发期 console 输出
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.error("[BuildHealth ErrorBoundary]", error, info.componentStack);
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, errorMessage: "" });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
          <div className="max-w-md w-full bg-white border border-slate-200 rounded-md shadow-sm p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 border border-red-300 rounded flex items-center justify-center text-red-600 font-bold">
                !
              </div>
              <div>
                <div className="text-base font-semibold text-slate-900">
                  BuildHealth
                </div>
                <div className="text-sm text-red-700">
                  Something went wrong
                </div>
              </div>
            </div>

            <p className="text-sm text-slate-700 leading-relaxed mb-3">
              The interface encountered an unexpected error and could not
              continue rendering. Your data and session are unaffected.
            </p>

            <div className="bg-slate-50 border border-slate-200 rounded px-3 py-2 text-xs text-slate-600 font-mono mb-4">
              {this.state.errorMessage}
            </div>

            <div className="flex gap-2">
              <button
                onClick={this.handleReset}
                className="flex-1 px-3 py-2 text-sm border border-slate-300 rounded text-slate-700 hover:bg-slate-50"
              >
                Try Again
              </button>
              <button
                onClick={this.handleReload}
                className="flex-1 px-3 py-2 text-sm bg-blue-700 text-white rounded hover:bg-blue-800"
              >
                Reload Page
              </button>
            </div>

            <p className="text-[11px] text-slate-400 mt-4 leading-relaxed">
              If this persists, contact the BuildHealth engineering team. All
              data displayed here is simulated and prototype parameters only.
            </p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
