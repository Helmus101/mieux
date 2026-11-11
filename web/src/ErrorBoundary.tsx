import { Component, type ReactNode } from 'react';
import { t } from '@shared/i18n';
import { report } from './report';

/** A screen that fails to load or render shows a way out instead of a blank page. A stale or half-downloaded script gets one automatic reload. */
export default class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(e: Error) {
    console.error(e);
    const chunk = /Loading chunk|dynamically imported module|Importing a module script failed|Unexpected token '<'/i.test(e.message);
    report(chunk ? 'chunk' : 'boundary', e);
    try { if (chunk && !sessionStorage.getItem('mieux_reloaded')) { sessionStorage.setItem('mieux_reloaded', '1'); location.reload(); } } catch { /* storage unavailable */ }
  }
  componentDidUpdate(prev: { resetKey?: string }) { if (this.state.failed && prev.resetKey !== this.props.resetKey) this.setState({ failed: false }); }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="screen" style={{ textAlign: 'center', paddingTop: 80 }}>
        <h2 style={{ textTransform: 'none', letterSpacing: 0, fontSize: 22, color: 'var(--ink)' }}>{t('common.error')}</h2>
        <p className="mut">{t('common.slow')}</p>
        <button className="btn primary" onClick={() => location.reload()}>{t('common.reload')}</button>
      </div>
    );
  }
}
