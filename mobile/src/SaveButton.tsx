import { Pressable, Text } from 'react-native';
import { useHistory } from '@shared/stores';
import { t } from '@shared/i18n';
import { useTheme } from './ui';
import * as hx from './haptics';

/* eslint-disable @typescript-eslint/no-explicit-any */
/** Bookmark toggle: adds a product to (or removes it from) the saved list. */
export default function SaveButton({ product }: { product: any }) {
  const c = useTheme();
  const saved = useHistory((s) => s.saved.some((x) => x.id === product?.id));
  const toggle = useHistory((s) => s.toggleSaved);
  if (!product?.id) return null;
  return (
    <Pressable accessibilityRole="button" accessibilityState={{ selected: saved }} accessibilityLabel={t(saved ? 'list.saved' : 'list.save')}
      onPress={() => { if (saved) hx.light(); else hx.success(); toggle(product); }}
      hitSlop={8} style={{ paddingHorizontal: 10, paddingVertical: 6, borderRadius: 10, backgroundColor: saved ? c.tint : 'transparent' }}>
      <Text style={{ fontSize: 20, color: saved ? c.accent : c.mut }}>{saved ? '★' : '☆'}</Text>
    </Pressable>
  );
}
