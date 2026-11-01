// Platform-free design tokens. On web they are mirrored as CSS variables (web/src/index.css);
// in Expo import this file directly and use it in StyleSheet.create.
export const colors = {
  // The landing page palette: warm paper, ink, leaf green, sage tint. Nutri-Score and NOVA keep their official colours below.
  light: { bg: '#F7F3E8', card: '#FFFDF6', ink: '#14201A', mut: '#5C6A60', line: 'rgba(31,77,58,0.16)', accent: '#1F4D3A', accentInk: '#F7F3E8', tint: '#E6EDDC', warn: '#B85C38', bad: '#A33B2B', blue: '#1F4D3A' },
  dark: { bg: '#0F1712', card: '#16211A', ink: '#F3EFE3', mut: '#A9B6AB', line: '#26332B', accent: '#DCF06A', accentInk: '#101A12', tint: 'rgba(220,240,106,0.12)', warn: '#E0A24A', bad: '#E4695A', blue: '#9CBE77' },
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
