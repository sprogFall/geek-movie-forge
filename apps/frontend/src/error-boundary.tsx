import { Component, type ErrorInfo, type ReactNode } from "react";

type AppErrorBoundaryProps = {
  children: ReactNode;
};

type AppErrorBoundaryState = {
  error: Error | null;
};

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = {
    error: null,
  };

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("AppErrorBoundary", error, errorInfo);
  }

  private handleRetry = () => {
    this.setState({ error: null });
  };

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <main className="loading-screen">
        <div className="panel error-panel">
          <div className="stack-sm">
            <p className="eyebrow">错误</p>
            <h2>页面运行异常</h2>
            <p className="error-panel-copy">
              {this.state.error.message || "前端运行时发生异常，请重试或刷新页面。"}
            </p>
            <div className="form-actions">
              <button className="btn btn-primary" type="button" onClick={this.handleRetry}>
                重试
              </button>
              <button className="btn btn-secondary" type="button" onClick={() => window.location.reload()}>
                刷新页面
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }
}
