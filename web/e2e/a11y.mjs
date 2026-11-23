// Accessibility gate: opens each screen of the built app (npm run build && npm run preview) in a real browser and runs axe-core.
// Any violation fails the run, so a regression is caught before it ships.   Usage: node e2e/a11y.mjs [baseUrl]
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

const BASE = process.argv[2] || 'http://127.0.0.1:4173';
const axeSrc = readFileSync(createRequire(import.meta.url).resolve('axe-core/axe.min.js'), 'utf8');
const PROFILE = { onboarded: true, priorities: ['value'], diet: 'omnivore', allergens: [], name: '', place: null, chains: [], strictAdditives: true, country: 'FR', language: 'fr' };
// The screens that need no data from the API. The API is stubbed (empty answers), so the run needs no backend and counts no visit.
const SCREENS = [['landing', '/', false], ['onboarding', '/app', false], ['scan', '/app/scan', true], ['list', '/app/list', true], ['history', '/app/history', true], ['profile', '/app/profile', true], ['blog', '/blog', false]];

const browser = await chromium.launch();
let failed = 0;
for (const [name, path, onboarded] of SCREENS) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'fr-FR' });
  await ctx.addInitScript((p) => { try { localStorage.setItem('mx_no_count', '1'); if (p.on) localStorage.setItem('fiq_profile', JSON.stringify(p.profile)); } catch { /* storage unavailable */ } }, { on: onboarded, profile: PROFILE });
  await ctx.route('**/v1/**', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }));
  const page = await ctx.newPage();
  await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);
  await page.evaluate(axeSrc);
  const violations = await page.evaluate(async () => (await axe.run(document)).violations.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.slice(0, 3).map((n) => n.target.join(' ')) })));
  console.log(`${violations.length ? 'FAIL' : 'ok  '} ${name}${violations.length ? ': ' + violations.map((v) => `${v.id} [${v.impact}] ${v.nodes.join(', ')}`).join(' | ') : ''}`);
  if (violations.length) failed++;
  await ctx.close();
}
await browser.close();
process.exit(failed ? 1 : 0);
