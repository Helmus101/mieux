import { useRef, useState } from 'react';
import { Pressable, SafeAreaView, StyleSheet, Text, View } from 'react-native';
import { CameraView, scanFromURLAsync, useCameraPermissions } from 'expo-camera';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { api } from '@shared/api/client';
import { validBarcode } from '@shared/barcode';
import { t } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { Button, Card, LargeTitle, Muted, Row, Screen, useTheme } from '../src/ui';
import { routes, useNav } from '../src/nav';
import * as hx from '../src/haptics';

// Products are identified by scanning their barcode only: no typed codes, no name search.
export default function Scan() {
  const c = useTheme();
  const router = useRouter();
  const { go } = useNav();
  const { compare } = useLocalSearchParams<{ compare?: string }>();
  const forCompare = compare === '1';   // opened from Compare: add the scanned product there instead of opening it
  const addCompare = useProfile((s) => s.addCompare);
  const [perm, ask] = useCameraPermissions();
  const [torch, setTorch] = useState(false);
  const done = useRef(false);
  const [msg, setMsg] = useState('');
  const [picking, setPicking] = useState(false);

  const open = (code: string) => {
    if (forCompare) { addCompare(code); router.replace(routes.compare); }
    else go(routes.product(code));
  };
  const onCode = ({ data }: { data: string }) => {
    if (done.current || picking || !validBarcode(data)) return; // the check digit filters mis-reads; the first valid code wins
    done.current = true; hx.success();
    api.getProduct(data).catch(() => undefined);
    open(data);
    setTimeout(() => { done.current = false; }, 2000);
  };
  // Same as the web scanner: a photo of the barcode works when the live camera does not.
  const fromGallery = async () => {
    if (picking) return;
    setMsg(''); setPicking(true);   // the live camera ignores detections while a photo is being chosen and read
    try {
      const r = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 1 });
      const uri = r.canceled ? null : r.assets?.[0]?.uri;
      if (!uri) return;
      const found = (await scanFromURLAsync(uri, ['ean13', 'ean8', 'upc_a', 'upc_e'])).map((x) => x.data).find(validBarcode);
      if (found) { setPicking(false); onCode({ data: found }); } else { hx.error(); setMsg(t('scan.noCode')); }
    } catch { hx.error(); setMsg(t('scan.noCode')); } finally { setPicking(false); }
  };
  // Closing goes back where the person came from; from Compare, back to the comparison.
  const close = () => { if (forCompare) router.replace(routes.compare); else if (router.canGoBack()) router.back(); else router.replace(routes.list); };

  if (!perm?.granted) return (
    <Screen>
      <LargeTitle sub={t('simple.scanSub')}>{t('scan.title')}</LargeTitle>
      <Card><Text style={{ color: c.ink, fontSize: 17, fontWeight: '600' }}>{t('simple.camNeeded')}</Text><Muted>{t('scan.hint')}</Muted><Button primary onPress={ask}>{t('scan.open')}</Button></Card>
      <Button plain onPress={close}>{t('common.cancel')}</Button>
    </Screen>
  );
  // Granted: the camera fills the screen (no scrolling); the frame, the one-line instruction and the torch sit on top of it.
  return (
    <View style={{ flex: 1, backgroundColor: '#000' }}>
      <CameraView style={StyleSheet.absoluteFill} facing="back" enableTorch={torch} onBarcodeScanned={onCode} barcodeScannerSettings={{ barcodeTypes: ['ean13', 'ean8', 'upc_a', 'upc_e'] }} />
      <View pointerEvents="none" style={{ position: 'absolute', left: '12%', right: '12%', top: '32%', bottom: '38%', borderWidth: 2, borderColor: '#ffffffd9', borderRadius: 16 }} />
      <SafeAreaView pointerEvents="box-none" style={{ flex: 1, justifyContent: 'space-between' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16 }}><Pressable onPress={close} accessibilityLabel={t('common.back')} hitSlop={12}><Text style={{ color: '#fff', fontSize: 28 }}>✕</Text></Pressable></View>
        <Text style={{ color: '#fff', textAlign: 'center', fontSize: 16, fontWeight: '600', marginTop: 16, textShadowColor: '#0008', textShadowRadius: 6 }}>{forCompare ? t('compare.scanForCompare') : t('scan.point')}</Text>
        <View style={{ alignItems: 'center', marginBottom: 20 }}>{msg ? <Text style={{ color: '#fff', marginBottom: 8 }}>{msg}</Text> : null}<Row><Button small plain onPress={() => setTorch(!torch)}>{t('scan.torch')}{torch ? ' · on' : ''}</Button><Button small plain onPress={fromGallery}>{msg ? t('scan.retry') : t('scan.gallery')}</Button></Row></View>
      </SafeAreaView>
    </View>
  );
}
