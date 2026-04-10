import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: error?.message || 'Unknown render error',
    };
  }

  componentDidCatch(error, errorInfo) {
    // Keep details in console for local debugging.
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.errorMessage);
      }
      return (
        <div style={{
          background: 'var(--color-surface-floating)',
          border: '1px solid var(--color-border)',
          borderRadius: '10px',
          padding: '16px',
          color: 'var(--color-text-primary)'
        }}>
          <div style={{ fontWeight: 700, marginBottom: '8px' }}>Component failed to render.</div>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>{this.state.errorMessage}</div>
        </div>
      );
    }

    return this.props.children;
  }
}
