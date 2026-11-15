// Mieux launch video. Numbers are from the real example on the landing page (captured 2026-11-09 from Open Food Facts and Open Prices).
export default {
  hook(s) {
    const { top, h, w } = s.safe;
    const u = Math.min(w, h) / 100;
    s.icon('shopping-cart', { y: top + h * 0.3, size: u * 17, color: 'accent', bg: 'circle', at: -1 });
    s.text('Worth its price?', { y: top + h * 0.6, size: u * 10, at: '#q' });
    s.text('What to buy *instead*?', { y: top + h * 0.78, size: u * 7, color: 'muted', at: '#alt' });
  },

  scan(s) {
    const { left, top, w, h } = s.safe;
    const u = Math.min(w, h) / 100;
    const xs = s.portrait ? [s.cx, s.cx] : [left + w * 0.27, left + w * 0.73];
    const ys = s.portrait ? [top + h * 0.28, top + h * 0.72] : [s.cy, s.cy];
    s.box('Dark chocolate 70%\n100 g', { id: 'bar', x: xs[0], y: ys[0], size: u * 5.5, icon: 'barcode', at: 0.3 });
    s.annotate('bar', { type: 'bracket', color: 'accent', at: '#name' });
    const n = s.number(43, { x: xs[1] - u * 4, y: ys[1] - u * 4, size: u * 17, color: '#B8480A', at: '#score' });
    s.text('/100', { x: n.right + u * 6, y: n.bottom - u * 5, size: u * 6, color: 'muted', at: '#score' });
    s.text('€24.35 per kilo', { x: xs[1], y: n.bottom + u * 8, size: u * 6, at: '#score' });
  },

  alternatives(s) {
    const { w, h } = s.safe;
    const u = Math.min(w, h) / 100;
    const cards = [
      { t: 'Cheapest', price: '€14.80/kg', note: '45/100', diff: '39% less', color: 'green', at: '#c1' },
      { t: 'Best quality', price: '€31.20/kg', note: '54/100', diff: '', color: 'blue', at: '#c2' },
      { t: 'Best value', price: '€18.70/kg', note: '49/100', diff: '23% less', color: 'accent', at: '#c3' },
    ];
    s.text('Same shelf, three ways to choose', { y: s.safe.top + h * (s.portrait ? 0.06 : 0.1), size: u * (s.portrait ? 5.5 : 6.5), maxWidth: w, at: 0.3 });
    if (s.portrait) {
      const { left, top } = s.safe;
      cards.forEach((c, i) => {
        const y = top + h * (0.3 + i * 0.27);
        s.box(c.t, { x: left + w * 0.28, y, size: u * 5.5, color: c.color, at: c.at });
        s.text(c.price, { x: left + w * 0.76, y: y - u * 4, size: u * 6, bold: true, at: c.at });
        s.text(c.diff ? c.note + ' · ' + c.diff : c.note, { x: left + w * 0.76, y: y + u * 5, size: u * 4.6, color: c.diff ? 'green' : 'muted', at: c.at });
      });
      return;
    }
    const xs = s.row(3, { width: w * 0.86 });
    const ys = [0, 0, 0].map(() => s.cy + h * 0.06);
    cards.forEach((c, i) => {
      const b = s.box(c.t, { x: xs[i], y: ys[i] - u * 8, size: u * 6, color: c.color, at: c.at });
      s.text(c.price, { x: xs[i], y: b.bottom + u * 7, size: u * 7, bold: true, at: c.at });
      s.text(c.note, { x: xs[i], y: b.bottom + u * 14, size: u * 5, color: 'muted', at: c.at });
      if (c.diff) s.text(c.diff, { x: xs[i], y: b.bottom + u * 20, size: u * 5, color: 'green', at: c.at });
    });
  },

  honest(s) {
    const { left, top, w, h } = s.safe;
    const u = Math.min(w, h) / 100;
    const xs = s.portrait ? [left + w * 0.22, left + w * 0.78, s.cx] : [left + w * 0.2, left + w * 0.2, left + w * 0.8];
    const ys = s.portrait ? [top + h * 0.12, top + h * 0.12, top + h * 0.78] : [s.cy - h * 0.2, s.cy + h * 0.2, s.cy];
    s.box('Open Prices', { id: 'op', x: xs[0], y: ys[0], size: u * 5.5, icon: 'database', at: 0.3 });
    s.box('Your receipts', { id: 'rc', x: xs[1], y: ys[1], size: u * 5.5, icon: 'receipt', at: 0.5 });
    s.box('Real price', { id: 'rp', x: s.cx, y: s.portrait ? top + h * 0.45 : s.cy, size: u * 6, color: 'green', at: '#src' });
    s.arrow('op', 'rp', { at: '#src' });
    s.arrow('rc', 'rp', { at: '#src' });
    s.box('Unknown price', { id: 'un', x: xs[2], y: ys[2], size: u * 5.5, dashed: true, color: 'muted', at: '#unknown' });
    s.text('Said as unknown', { x: xs[2], y: ys[2] + u * 11, size: u * 5, color: 'muted', at: '#unknown' });
    s.annotate('un', { type: 'cross', color: 'red', at: '#never' });
  },

  privacy(s) {
    const { w, h } = s.safe;
    const u = Math.min(w, h) / 100;
    const items = [
      { icon: 'smartphone', label: 'Scans stay on your phone', at: 0.3 },
      { icon: 'gift', label: 'Free, nothing to install', at: '#free' },
    ];
    const xs = s.portrait ? [s.cx, s.cx] : s.row(2, { width: w * 0.6 });
    const ys = s.portrait ? [s.safe.top + h * 0.22, s.safe.top + h * 0.62] : [s.cy, s.cy];
    items.forEach((it, i) => s.icon(it.icon, { x: xs[i], y: ys[i], size: u * 15, bg: 'circle', color: 'accent', label: it.label, labelSize: u * 5, at: it.at }));
  },

  outro(s) {
    const { top, h, w } = s.safe;
    const u = Math.min(w, h) / 100;
    s.title('Mieux', { y: top + h * 0.3, size: u * 15, at: -1 });
    const items = ['Watch', 'Like', 'Share'];
    const xs = s.row(3, { width: w * (s.portrait ? 0.78 : 0.6) });
    const ys = items.map(() => top + h * 0.58);
    items.forEach((t, i) => s.box(t, { x: xs[i], y: ys[i], size: u * 6, color: 'accent', icon: ['play', 'thumbs-up', 'share-2'][i], at: '#ask' }));
    s.subtitle('Help us win the Audience Vote', { y: top + h * 0.88, size: u * 5.5, maxWidth: w, at: '#vote' });
  },
};
