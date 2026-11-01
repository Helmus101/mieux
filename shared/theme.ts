// Platform-free design tokens. On web they are mirrored as CSS variables (web/src/index.css);
// in Expo import this file directly and use it in StyleSheet.create.
export const colors = {
  light: { bg: '#F2F2F7', card: '#FFFFFF', ink: '#000000', mut: '#8E8E93', line: 'rgba(60,60,67,0.18)', accent: '#34C759', accentInk: '#FFFFFF', tint: 'rgba(52,199,89,0.14)', warn: '#FF9500', bad: '#FF3B30', blue: '#0A84FF' },
  dark: { bg: '#000000', card: '#1C1C1E', ink: '#FFFFFF', mut: '#8E8E93', line: 'rgba(84,84,88,0.55)', accent: '#30D158', accentInk: '#000000', tint: 'rgba(48,209,88,0.18)', warn: '#FF9F0A', bad: '#FF453A', blue: '#0A84FF' },
};
export const radius = { sm: 10, md: 14, lg: 20, pill: 999 };
export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 };
export const font = {
  family: '-apple-system, "SF Pro Text", "SF Pro Display", system-ui, "Helvetica Neue", sans-serif',
  largeTitle: { size: 34, weight: '700' }, title: { size: 22, weight: '700' }, headline: { size: 17, weight: '600' },
  body: { size: 17, weight: '400' }, callout: { size: 16, weight: '400' }, footnote: { size: 13, weight: '400' }, caption: { size: 12, weight: '400' },
};
export const novaColors: Record<number, string> = { 1: '#038141', 2: '#85BB2F', 3: '#EE8100', 4: '#E63E11' };
export const nutriScoreColors: Record<string, string> = { a: '#038141', b: '#85BB2F', c: '#FECB02', d: '#EE8100', e: '#E63E11' };
