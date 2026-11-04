import { afterEach, describe, expect, it, vi } from 'vitest';
import { isPhone, platform, wantsLanding } from './install';

const ua = (userAgent: string, extra: Record<string, unknown> = {}) => vi.stubGlobal('navigator', { userAgent, platform: 'x', maxTouchPoints: 0, ...extra });

describe('install hint platform detection', () => {
  afterEach(() => { vi.unstubAllGlobals(); });
  it('detects iPhone, iPad (desktop-class UA) and Android', () => {
    ua('Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) Safari/604.1'); expect(platform()).toBe('ios');
    ua('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1', { platform: 'MacIntel', maxTouchPoints: 5 }); expect(platform()).toBe('ios');
    ua('Mozilla/5.0 (Linux; Android 14; Pixel 8) Chrome/124.0 Mobile Safari/537.36'); expect(platform()).toBe('android');
  });
  it('shows no hint on a desktop computer', () => {
    ua('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/124.0 Safari/537.36', { platform: 'MacIntel' }); expect(platform()).toBe('other');
  });
});

describe('who gets the landing page', () => {
  afterEach(() => { vi.unstubAllGlobals(); });
  it('treats every touch device as app-first', () => {
    ua('Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) Safari/604.1'); expect(isPhone()).toBe(true);
    ua('Mozilla/5.0 (Linux; Android 14; Pixel 8) Chrome/124.0 Mobile Safari/537.36'); expect(isPhone()).toBe(true);
    ua('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1', { platform: 'MacIntel', maxTouchPoints: 5 }); expect(isPhone()).toBe(true); // iPad
    ua('Mozilla/5.0 (Linux; Android 13; SM-X710) Chrome/124.0 Safari/537.36'); expect(isPhone()).toBe(true); // Android tablet
  });
});

describe('landing page vs app', () => {
  const at = (pathname: string, search = '') => {
    vi.stubGlobal('window', { location: { pathname, search }, matchMedia: () => ({ matches: false }) });
    vi.stubGlobal('sessionStorage', { getItem: () => '1' });   // as if the app had already been opened in this tab
  };
  afterEach(() => { vi.unstubAllGlobals(); });
  it('a computer sees the landing page at the root only', () => {
    ua('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/124.0 Safari/537.36', { platform: 'MacIntel' });
    at('/'); expect(wantsLanding()).toBe(true);
    at('/app'); expect(wantsLanding()).toBe(false);            // the app's own URL never shows the landing
    at('/', '?app'); expect(wantsLanding()).toBe(false);       // ?app skips it on purpose
  });
  it('a phone goes straight to the app', () => {
    ua('Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) Safari/604.1');
    at('/'); expect(wantsLanding()).toBe(false);
  });
  it('an iPad goes straight to the app', () => {
    ua('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1', { platform: 'MacIntel', maxTouchPoints: 5 });
    at('/'); expect(wantsLanding()).toBe(false);
  });
  it('a computer gets the landing page even after opening the app, and in an installed window', () => {
    ua('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/124.0 Safari/537.36', { platform: 'MacIntel' });
    at('/'); expect(wantsLanding()).toBe(true);            // the app was already opened in this tab
    vi.stubGlobal('window', { location: { pathname: '/', search: '' }, matchMedia: () => ({ matches: true }) });
    expect(wantsLanding()).toBe(true);                     // installed desktop app window, still at the root
  });
});
