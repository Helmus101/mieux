import { useState } from 'react';
import { Pressable } from 'react-native';
import { t } from '@shared/i18n';
import { Body, Muted, Sheet, haptic } from './ui';
import { useTheme } from '@/lib/theme';

/** A small "?" that opens a plain-language explanation of the value score. */
export default function PqExplain() {
  const [open, setOpen] = useState(false), c = useTheme();
  return <>
    <Pressable hitSlop={10} accessibilityLabel={t('score.pqWhatTitle')} onPress={() => { haptic('select'); setOpen(true); }}><Muted small style={{ color: c.accent, fontWeight: '700' }}> ?</Muted></Pressable>
    <Sheet open={open} onClose={() => setOpen(false)} title={t('score.pqWhatTitle')}>
      <Body>{t('score.pqWhat1')}</Body><Body>{t('score.pqWhat2')}</Body><Muted small>{t('score.pqWhat3')}</Muted>
    </Sheet>
  </>;
}
