import { Tabs } from 'expo-router';
import { StyleSheet } from 'react-native';
import { BlurView } from 'expo-blur';
import { Ionicons } from '@expo/vector-icons';
import { t } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { haptic } from '@/components/ui';
import { useTheme } from '@/lib/theme';

type Name = keyof typeof Ionicons.glyphMap;
const icon = (on: Name, off: Name) => ({ color, focused }: { color: unknown; focused: boolean }) => <Ionicons name={focused ? on : off} size={25} color={color as string} />;

/** Translucent tab bar (content scrolls under it), hairline on top, strong haptic on every tab press. */
export default function TabsLayout() {
  const c = useTheme();
  useProfile((s) => s.language);   // re-render the labels when the language changes
  return (
    <Tabs screenListeners={{ tabPress: () => haptic('select') }}
      screenOptions={{
        headerShown: false, tabBarActiveTintColor: c.accent, tabBarInactiveTintColor: c.mut,
        tabBarLabelStyle: { fontSize: 10.5, fontWeight: '500' },
        tabBarStyle: { position: 'absolute', backgroundColor: 'transparent', borderTopColor: c.line, borderTopWidth: StyleSheet.hairlineWidth, elevation: 0 },
        tabBarBackground: () => <BlurView intensity={70} tint="light" style={StyleSheet.absoluteFill} />,
      }}>
      <Tabs.Screen name="list" options={{ title: t('tabs.list'), tabBarIcon: icon('list', 'list-outline') }} />
      <Tabs.Screen name="scan" options={{ title: t('tabs.scan'), tabBarIcon: icon('scan', 'scan-outline') }} />
      <Tabs.Screen name="profile" options={{ title: t('tabs.profile'), tabBarIcon: icon('person', 'person-outline') }} />
    </Tabs>
  );
}
