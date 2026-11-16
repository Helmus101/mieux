import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useProfile } from '@shared/stores';
import { boot } from '@/lib/boot';
import { Loader } from '@/components/ui';
import { useTheme } from '@/lib/theme';

/** Waits for the stored profile to load (the shared stores are synchronous), then routes to onboarding or the app. */
export default function Root() {
  const [ready, setReady] = useState(false);
  const c = useTheme();
  useEffect(() => { boot().finally(() => setReady(true)); }, []);
  if (!ready) return <View style={{ flex: 1, backgroundColor: c.bg, justifyContent: 'center' }}><Loader /></View>;
  return (
    <SafeAreaProvider>
      <StatusBar style="auto" />
      <Gate />
    </SafeAreaProvider>
  );
}

function Gate() {
  const onboarded = useProfile((s) => s.onboarded);
  const router = useRouter(), seg = useSegments();
  const c = useTheme();
  useEffect(() => {
    const inOb = seg[0] === 'onboarding';
    if (!onboarded && !inOb) router.replace('/onboarding');
    else if (onboarded && inOb) router.replace('/scan');
  }, [onboarded, seg, router]);
  return <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.bg } }} />;
}
