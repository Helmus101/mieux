import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { t } from '@shared/i18n';
import { useHistory, useProfile } from '@shared/stores';
import { Body, Button, Cell, Confirm, Group, LargeTitle, Muted, Screen } from '@/components/ui';
import { useTheme } from '@/lib/theme';

/** Saved products, plus the compare and history tools. */
export default function List() {
  const r = useRouter(), c = useTheme();
  useProfile((s) => s.language);
  const saved = useHistory((s) => s.saved), remove = useHistory((s) => s.removeSaved), clearSaved = useHistory((s) => s.clearSaved);
  const [ask, setAsk] = useState(false);
  return (
    <Screen title={t('tabs.list')} bottom={110}>
      <LargeTitle sub={saved.length ? t('list.count', { n: saved.length }) : undefined}>{t('tabs.list')}</LargeTitle>
      {saved.length ? <>
        <Group>{saved.map((s) => (
          <Cell key={s.id} image={s.product.imageUrl || null} chevron onPress={() => r.push(`/product/${s.id}`)}
            right={<Pressable hitSlop={10} onPress={() => remove(s.id)} accessibilityLabel={t('list.remove')}><Text style={{ color: c.mut, fontSize: 18 }}>✕</Text></Pressable>}>
            <Body bold>{s.product.name}</Body>
            <Muted small>{[s.product.brand, s.product.score ? `${s.product.score.total}/100` : null].filter(Boolean).join(' · ')}</Muted>
          </Cell>
        ))}</Group>
        <Button danger onPress={() => setAsk(true)}>{t('list.clear')}</Button>
        <Confirm open={ask} onClose={() => setAsk(false)} onConfirm={clearSaved} title={t('list.clear')} action={t('common.delete')}>{t('list.clearConfirm')}</Confirm>
      </> : <View style={{ gap: 12, paddingVertical: 24 }}><Muted>{t('list.empty')}</Muted><Button primary onPress={() => r.push('/scan')}>{t('tabs.scan')}</Button></View>}
      <Group>
        <Cell chevron onPress={() => r.push('/compare')}><Body bold>{t('list.compareTool')}</Body></Cell>
        <Cell chevron onPress={() => r.push('/history')}><Body bold>{t('list.historyTool')}</Body></Cell>
      </Group>
    </Screen>
  );
}
