import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { t } from '@shared/i18n';
import { colors } from '@shared/theme';
import { useColorScheme } from 'react-native';
import { select } from '../../src/haptics';

// expo-router: the tab group opens on the scanner
export const unstable_settings = { initialRouteName: 'scan' };

export default function TabsLayout() {
  const c = colors[useColorScheme() === 'dark' ? 'dark' : 'light'];
  const icon = (name: keyof typeof Ionicons.glyphMap) => ({ color, size }: { color: string | unknown; size: number }) => <Ionicons name={name} color={color as string} size={size} />;
  return (
    <Tabs screenListeners={{ tabPress: () => select() }} screenOptions={{ headerShown: false, tabBarActiveTintColor: c.accent, tabBarInactiveTintColor: c.mut, tabBarStyle: { backgroundColor: c.card } }}>
      <Tabs.Screen name="index" options={{ href: null }} />
      <Tabs.Screen name="compare" options={{ href: null }} />
      <Tabs.Screen name="scan" options={{ tabBarStyle: { display: 'none' }, title: t('tabs.scan'), tabBarIcon: icon('barcode-outline') }} />
      <Tabs.Screen name="purchases" options={{ title: t('tabs.purchases'), tabBarIcon: icon('receipt-outline') }} />
      <Tabs.Screen name="profile" options={{ title: t('tabs.profile'), tabBarIcon: icon('person-outline') }} />
    </Tabs>
  );
}
