import React from 'react';

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('RealityShield frontend error:', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <main className="app-error" role="alert">
          <h1>Dashboard could not start</h1>
          <p>{this.state.error.message || 'An unexpected frontend error occurred.'}</p>
          <button type="button" onClick={() => window.location.reload()}>Reload dashboard</button>
        </main>
      );
    }

    return this.props.children;
  }
}

export default AppErrorBoundary;
