import { Pressable, Text, View } from 'react-native';
import { Tabs, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { t } from '@shared/i18n';
import { useTheme } from '../../src/ui';
import * as hx from '../../src/haptics';

// Same three destinations as the web app: the saved list, the scanner (centre), the profile.
export const unstable_settings = { initialRouteName: 'list' };

/* eslint-disable @typescript-eslint/no-explicit-any */
function Bar({ state, navigation }: any) {
  const c = useTheme(); const router = useRouter(); const insets = useSafeAreaInsets();
  const at = (name: string) => state.routes.findIndex((r: any) => r.name === name) === state.index;
  const item = (name: string, label: string, icon: keyof typeof Ionicons.glyphMap) => (
    <Pressable key={name} onPress={() => { hx.select(); navigation.navigate(name); }} style={{ flex: 1, alignItems: 'center', paddingTop: 8, paddingBottom: 4 }}>
      <Ionicons name={icon} size={24} color={at(name) ? c.accent : c.mut} />
      <Text style={{ color: at(name) ? c.accent : c.mut, fontSize: 11, marginTop: 2 }}>{label}</Text>
    </Pressable>
  );
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', paddingBottom: insets.bottom, backgroundColor: c.card, borderTopWidth: 1, borderTopColor: c.line }}>
      {item('list', t('tabs.list'), at('list') ? 'bookmark' : 'bookmark-outline')}
      <Pressable onPress={() => { hx.medium(); router.push('/scan'); }} style={{ flex: 1, alignItems: 'center' }} accessibilityLabel={t('tabs.scan')}>
        <View style={{ width: 58, height: 58, borderRadius: 29, marginTop: -20, backgroundColor: c.accent, alignItems: 'center', justifyContent: 'center', shadowColor: c.accent, shadowOpacity: 0.35, shadowRadius: 10, shadowOffset: { width: 0, height: 4 }, elevation: 5 }}>
          <Ionicons name="barcode-outline" size={27} color={c.accentInk} />
        </View>
        <Text style={{ color: c.mut, fontSize: 11, marginBottom: 4 }}>{t('tabs.scan')}</Text>
      </Pressable>
      {item('profile', t('tabs.profile'), at('profile') ? 'person' : 'person-outline')}
    </View>
  );
}

export default function TabsLayout() {
  return (
    <Tabs tabBar={(p) => <Bar {...p} />} screenOptions={{ headerShown: false }}>
      <Tabs.Screen name="list" />
      <Tabs.Screen name="profile" />
    </Tabs>
  );
}
