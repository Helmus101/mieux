import { afterEach, describe, expect, it, vi } from 'vitest';
import { platform } from './install';

const ua = (userAgent: string, extra: Record<string, unknown> = {}) => vi.stubGlobal('navigator', { userAgent, platform: 'x', maxTouchPoints: 0, ...extra });

describe('install hint platform detection', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('detects iPhone, iPad (desktop-class UA) and Android', () => {
    ua('Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) Safari/604.1'); expect(platform()).toBe('ios');
    ua('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1', { platform: 'MacIntel', maxTouchPoints: 5 }); expect(platform()).toBe('ios');
    ua('Mozilla/5.0 (Linux; Android 14; Pixel 8) Chrome/124.0 Mobile Safari/537.36'); expect(platform()).toBe('android');
  });
  it('shows no hint on a desktop computer', () => {
    ua('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/124.0 Safari/537.36', { platform: 'MacIntel' }); expect(platform()).toBe('other');
  });
});
