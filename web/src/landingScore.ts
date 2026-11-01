// Simplified version of the app's strict score, for the landing-page simulator only: Nutri-Score 2023 points -> nutrition /60, additives /30, organic /10.
const pts = (v: number, th: number[]) => th.filter((x) => v > x).length;
const NQ: [number, number][] = [[-15, 100], [0, 92], [2, 76], [10, 48], [18, 20], [30, 4], [40, 0]];
const interp = (x: number, t: [number, number][]) => {
  if (x <= t[0][0]) return t[0][1];
  for (let i = 1; i < t.length; i++) if (x <= t[i][0]) return t[i - 1][1] + ((x - t[i - 1][0]) / (t[i][0] - t[i - 1][0])) * (t[i][1] - t[i - 1][1]);
  return t[t.length - 1][1];
};
export type Level = 'A' | 'B' | 'C' | 'D';
export interface DemoIn { sugar: number; sat: number; salt: number; kcal: number; add: Level; organic: boolean }
const ADD: Record<Level, number> = { A: 100, B: 85, C: 50, D: 0 };

export function demoScore(i: DemoIn) {
  const energy = pts(i.kcal * 4.184, Array.from({ length: 10 }, (_, k) => 335 * (k + 1)));
  const sugar = pts(i.sugar, [3.4, 6.8, 10, 14, 17, 20, 24, 27, 31, 34, 37, 41, 44, 48, 51]);
  const sat = pts(i.sat, Array.from({ length: 10 }, (_, k) => k + 1));
  const salt = pts(i.salt, Array.from({ length: 20 }, (_, k) => 0.2 * (k + 1)));
  const points = energy + sugar + sat + salt;
  const nutrition = 0.6 * interp(points, NQ), additives = 0.3 * ADD[i.add], organic = i.organic ? 10 : 0;
  let total = nutrition + additives + organic, capped = false;
  if (total > 49 && (i.add === 'D' || points >= 11)) { total = 49; capped = true; }  // Yuka-style: a high-risk additive or a D/E Nutri-Score cannot exceed 49
  return { total: Math.round(total), points, capped, nutrition, additives, organic, drivers: { energy, sugar, sat, salt } };
}
export const bandOf = (n: number) => (n >= 75 ? 'excellent' : n >= 50 ? 'good' : n >= 25 ? 'poor' : 'bad');
export const toneOf = (n: number) => (n >= 75 ? '#2E9E5B' : n >= 50 ? '#7DB840' : n >= 25 ? '#F2A33A' : '#E2503A');
