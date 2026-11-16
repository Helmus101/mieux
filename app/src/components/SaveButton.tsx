import { Pressable, Text } from 'react-native';
import { useHistory } from '@shared/stores';
import { t } from '@shared/i18n';
import { haptic } from './ui';
import { useTheme } from '@/lib/theme';

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function SaveButton({ product }: { product: any }) {
  const c = useTheme();
  const saved = useHistory((s) => s.saved.some((x) => x.id === product?.id)), toggle = useHistory((s) => s.toggleSaved);
  if (!product?.id) return null;
  return (
    <Pressable hitSlop={12} accessibilityLabel={t(saved ? 'list.saved' : 'list.save')} onPress={() => { haptic(saved ? 'tap' : 'success'); toggle(product); }}>
      <Text style={{ color: c.accent, fontSize: 24 }}>{saved ? '★' : '☆'}</Text>
    </Pressable>
  );
}
