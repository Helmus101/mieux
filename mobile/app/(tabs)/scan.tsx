import { useRef, useState } from 'react';
import { SafeAreaView, StyleSheet, Text, View } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { api } from '@shared/api/client';
import { validBarcode } from '@shared/barcode';
import { t } from '@shared/i18n';
import { Button, Card, LargeTitle, Muted, Screen, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';
import { success } from '../../src/haptics';

// Products are identified by scanning their barcode only: no typed codes, no name search.
export default function Scan() {
  const c = useTheme();
  const { go } = useNav();
  const [perm, ask] = useCameraPermissions();
  const [torch, setTorch] = useState(false);
  const done = useRef(false);
  const onCode = ({ data }: { data: string }) => {
    if (done.current || !validBarcode(data)) return; // the check digit filters mis-reads; the first valid code wins
    done.current = true; success();
    api.getProduct(data).catch(() => undefined); go(routes.product(data));
    setTimeout(() => { done.current = false; }, 2000);
  };
  if (!perm?.granted) return (
    <Screen>
      <LargeTitle sub={t('simple.scanSub')}>{t('scan.title')}</LargeTitle>
      <Card><Text style={{ color: c.ink, fontSize: 17, fontWeight: '600' }}>{t('simple.camNeeded')}</Text><Muted>{t('scan.hint')}</Muted><Button primary onPress={ask}>{t('scan.open')}</Button></Card>
    </Screen>
  );
  // Granted: the camera fills the screen (no scrolling); the frame, the one-line instruction and the torch sit on top of it.
  return (
    <View style={{ flex: 1, backgroundColor: '#000' }}>
      <CameraView style={StyleSheet.absoluteFill} facing="back" enableTorch={torch} onBarcodeScanned={onCode} barcodeScannerSettings={{ barcodeTypes: ['ean13', 'ean8', 'upc_a', 'upc_e'] }} />
      <View pointerEvents="none" style={{ position: 'absolute', left: '12%', right: '12%', top: '32%', bottom: '38%', borderWidth: 2, borderColor: '#ffffffd9', borderRadius: 16 }} />
      <SafeAreaView pointerEvents="box-none" style={{ flex: 1, justifyContent: 'space-between' }}>
        <Text style={{ color: '#fff', textAlign: 'center', fontSize: 16, fontWeight: '600', marginTop: 16, textShadowColor: '#0008', textShadowRadius: 6 }}>{t('scan.point')}</Text>
        <View style={{ alignItems: 'center', marginBottom: 20 }}><Button small plain onPress={() => setTorch(!torch)}>{t('scan.torch')}{torch ? ' · on' : ''}</Button></View>
      </SafeAreaView>
    </View>
  );
}
