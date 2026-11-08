import { useEffect, useState } from 'react';
import { ActivityIndicator, Image, Pressable, Text, View } from 'react-native';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import { useTheme } from './ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
/** A quick card over the live camera: title, score and a verdict. Tap for the full page; otherwise it leaves by itself and scanning goes on. */
export default function ScanPeek({ code, onOpen, onClose }: { code: string; onOpen: (code: string) => void; onClose: () => void }) {
  const c = useTheme();
  const [d, setD] = useState<any>(null), [failed, setFailed] = useState(false);
  const addScan = useHistory((s) => s.addScan);
  useEffect(() => {
    let live = true; setD(null); setFailed(false);
    api.getProduct(code).then((x: any) => { if (!live) return; setD(x); addScan(x.product); api.addScan(code).catch(() => undefined); }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [code]);
  useEffect(() => {
    if (!d && !failed) return;
    const timer = setTimeout(onClose, failed ? 3500 : 7000);
    return () => clearTimeout(timer);
  }, [d, failed, code]);
  const p = d?.product, sc = p?.score;
  const conflict = (d?.fit ?? []).some((x: any) => (x.priority.startsWith('allergen:') || x.priority.startsWith('diet:')) && x.status === 'conflict');
  const tone = conflict ? 'b' : sc?.tone;
  const color = tone === 'b' ? c.bad : tone === 'w' ? c.warn : c.accent;
  const pq: number | null = d?.price_context?.value?.value_score ?? null;
  const verdict = conflict ? t('scan.peekConflict') : sc ? t('score.' + sc.band) : t('score.na');
  return (
    <Pressable onPress={() => { if (p) onOpen(code); }} accessibilityRole="button" accessibilityLabel={t('scan.peekOpen')}
      style={{ position: 'absolute', left: 12, right: 12, bottom: 150, minHeight: 64, flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 18, backgroundColor: c.card, shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 14, elevation: 8 }}>
      {failed ? <Text style={{ color: c.mut }}>{t('scan.peekFailed')}</Text> : !p ? <ActivityIndicator /> : <>
        {p.imageUrl ? <Image source={{ uri: p.imageUrl }} style={{ width: 48, height: 48, borderRadius: 10, backgroundColor: '#fff' }} resizeMode="contain" /> : null}
        <View style={{ flex: 1 }}><Text numberOfLines={1} style={{ color: c.ink, fontWeight: '700', fontSize: 16 }}>{p.name}</Text><Text numberOfLines={1} style={{ color: c.mut }}>{p.brand ?? ''}</Text></View>
        <View style={{ alignItems: 'flex-end' }}><Text style={{ color, fontSize: 30, fontWeight: '700' }}>{sc ? sc.total : '–'}</Text><Text style={{ color, fontSize: 12, fontWeight: '600' }}>{verdict}</Text></View>
        <View style={{ alignItems: 'flex-end' }}><Text style={{ color: pq == null ? c.mut : pq >= 65 ? c.accent : pq >= 40 ? c.warn : c.bad, fontSize: 30, fontWeight: '700' }}>{pq ?? '–'}</Text><Text style={{ color: c.mut, fontSize: 12, fontWeight: '600' }}>{t('score.pq')}</Text></View>
      </>}
    </Pressable>
  );
}
