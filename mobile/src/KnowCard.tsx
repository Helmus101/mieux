import { Text, View } from 'react-native';
import { t } from '@shared/i18n';
import { Card, useTheme } from './ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
type Tone = 'g' | 'w' | 'b';
/** "What to know": the three things that matter at a glance, before the detail. Everything comes from the product's own score data. */
export default function KnowCard({ p }: { p: any }) {
  const c = useTheme();
  if (!p?.score) return null;
  const n: number | null | undefined = p.score.nutritional?.score;
  const nutrition: [string, Tone] | null = n == null ? null : n >= 70 ? ['good', 'g'] : n >= 45 ? ['ok', 'w'] : ['poor', 'b'];
  const items = (p.score.additives?.items ?? []) as any[];
  const additives: [string, Tone] = items.length === 0 ? ['none', 'g'] : items.some((x) => x.level === 'C' || x.level === 'D') ? ['watch', 'b'] : ['fine', 'g'];
  const nova = p.novaGroup ? { label: `NOVA ${p.novaGroup}`, tone: (p.novaGroup >= 4 ? 'b' : p.novaGroup === 3 ? 'w' : 'g') as Tone } : null;
  const rows: { k: string; label: string; tone: Tone; value: string }[] = [];
  if (nutrition) rows.push({ k: 'n', label: t('know.nutrition'), tone: nutrition[1], value: t('know.' + nutrition[0]) });
  rows.push({ k: 'a', label: t('know.additives'), tone: additives[1], value: t('know.' + additives[0]) });
  if (nova) rows.push({ k: 'p', label: t('know.processing'), tone: nova.tone, value: nova.label });
  const colour = (tone: Tone) => (tone === 'b' ? c.bad : tone === 'w' ? c.warn : c.accent);
  return (
    <Card>
      <Text style={{ color: c.mut, fontSize: 13, marginBottom: 6 }}>{t('know.title')}</Text>
      {rows.map((r) => (
        <View key={r.k} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 6 }}>
          <Text style={{ color: c.ink }}>{r.label}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: colour(r.tone) }} />
            <Text style={{ color: c.ink, fontWeight: '600' }}>{r.value}</Text>
          </View>
        </View>
      ))}
    </Card>
  );
}
