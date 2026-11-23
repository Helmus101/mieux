import { useCallback, useRef, useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { CameraView, Camera, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { validBarcode } from '@shared/barcode';
import { haptic } from '@/components/ui';
import ScanPeek from '@/components/ScanPeek';

const TYPES = ['ean13', 'ean8', 'upc_a', 'upc_e'] as const;
/** UPC-E / short codes are left as read; 12-digit UPC-A is what the backend expects for US products. */
const clean = (c: string) => c.replace(/\D/g, '');

/** Live barcode scanner. */
export default function Scan() {
  const r = useRouter();
  const [perm, ask] = useCameraPermissions();
  const [peek, setPeek] = useState<string | null>(null), [active, setActive] = useState(false), [torch, setTorch] = useState(false), [err, setErr] = useState('');
  const last = useRef({ code: '', at: 0 });
  const locked = useRef(false);   // the result sheet is open: the camera keeps running but a new barcode must not replace what is being read

  // The camera runs only while this tab is on screen.
  useFocusEffect(useCallback(() => { setActive(true); setErr(''); return () => { setActive(false); setTorch(false); setPeek(null); }; }, []));

  const open = (code: string) => {
    haptic('heavy');
    setPeek(code);   // the camera keeps running; the card shows the product, as on the web
  };
  const onScan = ({ data }: { data: string }) => {
    if (locked.current) return;
    const code = clean(data), now = Date.now();
    if (!validBarcode(code)) return;
    if (last.current.code === code && now - last.current.at < 3000) return;   // the same code is not opened twice
    last.current = { code, at: now };
    open(code);
  };
  const fromPhoto = async () => {
    setErr('');
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 1 });
    if (res.canceled || !res.assets[0]) return;
    const found = await Camera.scanFromURLAsync(res.assets[0].uri, [...TYPES]).catch(() => []);
    const code = found.map((f) => clean(f.data)).find(validBarcode);
    if (code) { api.getWebPriceQuick(code).catch(() => undefined); haptic('heavy'); r.push(`/product/${code}`); } else { haptic('error'); setErr(t('scan.noCode')); }
  };

  if (!perm) return <View style={s.fill} />;
  if (!perm.granted) return (
    <View style={[s.fill, s.center]}>
      <Text style={s.msg}>{t('simple.camNeeded')}</Text>
      <Pressable style={s.main} onPress={() => (perm.canAskAgain ? ask() : Linking.openSettings())}><Text style={s.mainTxt}>{t('scan.open')}</Text></Pressable>
      <Pressable onPress={fromPhoto}><Text style={s.link}>{t('scan.gallery')}</Text></Pressable>
      {err ? <Text style={[s.msg, { color: '#FF9A6B' }]}>{err}</Text> : null}
    </View>
  );
  return (
    <View style={s.fill}>
      {active && <CameraView style={StyleSheet.absoluteFill} facing="back" enableTorch={torch} barcodeScannerSettings={{ barcodeTypes: [...TYPES] }} onBarcodeScanned={onScan} />}
      <View style={s.mask} pointerEvents="none"><View style={s.frame} /></View>
      <View style={s.top}>
        <View />
        <Pressable style={[s.btn, torch && { backgroundColor: '#fff' }]} onPress={() => { haptic(); setTorch(!torch); }} accessibilityLabel={t('scan.torch')}><Text style={[s.btnTxt, torch && { color: '#000' }]}>⚡︎</Text></Pressable>
      </View>
      {peek && <ScanPeek code={peek} onClose={() => { locked.current = false; setPeek(null); }} onExpandedChange={(v) => { locked.current = v; }} />}
      <View style={s.bottom}>
        <Text style={s.msg}>{err || t('scan.point')}</Text>
        <Pressable onPress={fromPhoto}><Text style={s.link}>{t('scan.gallery')}</Text></Pressable>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  fill: { flex: 1, backgroundColor: '#000' },
  center: { alignItems: 'center', justifyContent: 'center', gap: 16, padding: 24 },
  mask: { ...StyleSheet.absoluteFill as object, alignItems: 'center', justifyContent: 'center' },
  frame: { width: '78%', aspectRatio: 1.6, borderRadius: 18, borderWidth: 3, borderColor: 'rgba(255,255,255,0.9)' },
  top: { position: 'absolute', top: 56, left: 16, right: 16, flexDirection: 'row', justifyContent: 'space-between' },
  btn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(0,0,0,0.45)', alignItems: 'center', justifyContent: 'center' },
  btnTxt: { color: '#fff', fontSize: 20 },
  bottom: { position: 'absolute', bottom: 28, left: 0, right: 0, alignItems: 'center', gap: 12, paddingHorizontal: 24 },
  msg: { color: '#fff', textAlign: 'center', fontSize: 16 },
  link: { color: '#fff', textDecorationLine: 'underline', fontSize: 15 },
  main: { backgroundColor: '#1F4D3A', paddingVertical: 14, paddingHorizontal: 24, borderRadius: 14 },
  mainTxt: { color: '#fff', fontWeight: '700', fontSize: 16 },
});
