import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

export default function App() {
  return (
    <>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="scan" options={{ title: 'Scan', headerShown: true }} />
        <Stack.Screen name="product/[barcode]" options={{ title: 'Product', headerShown: true }} />
        <Stack.Screen name="alternatives/[barcode]" options={{ title: 'Alternatives', headerShown: true }} />
        <Stack.Screen name="compare" options={{ title: 'Compare', headerShown: true }} />
        <Stack.Screen name="receipt/capture" options={{ title: 'Scan Receipt', headerShown: true }} />
        <Stack.Screen name="receipt/review" options={{ title: 'Review Receipt', headerShown: true }} />
      </Stack>
    </>
  );
}
