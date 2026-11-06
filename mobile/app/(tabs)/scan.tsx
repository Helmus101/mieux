import { useRef, useState } from 'react';
import { Text, View, Dimensions } from 'react-native';
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
  return (
    <Screen>
      <LargeTitle sub={t('simple.scanSub')}>{t('scan.title')}</LargeTitle>
      {!perm?.granted ? (
        <Card><Text style={{ color: c.ink, fontSize: 17, fontWeight: '600' }}>{t('simple.camNeeded')}</Text><Muted>{t('scan.hint')}</Muted><Button primary onPress={ask}>{t('scan.open')}</Button></Card>
      ) : (<>
        <View style={{ height: Math.round(Dimensions.get('window').height * 0.62), borderRadius: 28, overflow: 'hidden', backgroundColor: '#000' }}>
          <CameraView style={{ flex: 1 }} facing="back" enableTorch={torch} onBarcodeScanned={onCode} barcodeScannerSettings={{ barcodeTypes: ['ean13', 'ean8', 'upc_a', 'upc_e'] }} />
          <View pointerEvents="none" style={{ position: 'absolute', left: '10%', right: '10%', top: '30%', bottom: '30%', borderWidth: 3, borderColor: '#ffffffe6', borderRadius: 18 }} />
        </View>
        <View style={{ alignItems: 'center', marginTop: 12 }}><Muted>{t('scan.point')}</Muted><Button small plain onPress={() => setTorch(!torch)}>{t('scan.torch')}{torch ? ' · on' : ''}</Button></View>
      </>)}
    </Screen>
  );
}
