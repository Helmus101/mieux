// Platform-free design tokens. On web they are mirrored as CSS variables (web/src/index.css);
// in Expo import this file directly and use it in StyleSheet.create.
export const colors = {
  // One palette for web, landing and Expo (mirrored by the CSS variables in web/src/index.css): paper, ink, leaf green, sage tint. Nutri-Score and NOVA keep their official colours below.
  light: { bg: '#FAFAF7', card: '#F1F4F1', ink: '#17251D', mut: '#5A6660', line: 'rgba(15,26,21,0.12)', accent: '#1F4D3A', accentInk: '#FFFFFF', tint: '#EAF1ED', warn: '#D95A22', bad: '#A33B2B', blue: '#1F4D3A' },
  dark: { bg: '#0D1210', card: '#151C18', ink: '#F2F5F3', mut: '#A3AFA8', line: '#24302A', accent: '#6FCF97', accentInk: '#07140D', tint: 'rgba(111,207,151,0.14)', warn: '#FF9A6B', bad: '#E4695A', blue: '#9CBE77' },
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
