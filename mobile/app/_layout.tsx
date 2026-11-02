import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { api } from '@shared/api/client';
import { setApiBase, setStrict } from '@shared/config';
import { hydrateStores } from '@shared/hydrate';
import { useProfile } from '@shared/stores';
import Onboarding from '../src/Onboarding';
import { initStorage } from '../src/storage';
import { initHaptics } from '../src/haptics';
import { Platform } from 'react-native';

// EXPO_PUBLIC_API_URL must point at the FoodIQ backend. On a physical phone use your computer's LAN address (the backend must listen on it).
const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'https://mieux-api.fly.dev/v1';

export default function RootLayout() {
  const [ready, setReady] = useState(false);
  const { onboarded, priorities, diet, allergens } = useProfile();
  useEffect(() => { setApiBase(API_URL); setStrict(true); initStorage().then(() => { hydrateStores(); initHaptics(); setReady(true); }); }, []);
  useEffect(() => { if (ready && onboarded) api.updatePreferences({ diet, priorities, allergens } as never).catch(() => undefined); }, [ready, onboarded, priorities, diet, allergens]);
  if (!ready) return <View style={{ flex: 1, justifyContent: 'center', backgroundColor: '#FFFFFF' }}><ActivityIndicator size="large" color="#1F4D3A" /></View>;
  return (
    <SafeAreaProvider>
      <StatusBar style="auto" />
      {onboarded ? <Stack screenOptions={{ headerShown: false, animation: 'none' }} /> : <Onboarding />}
    </SafeAreaProvider>
  );
}
