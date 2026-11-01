import { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, Button, TouchableOpacity, TextInput } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { router } from 'expo-router';
import { api } from '@shared/api/client';

export default function ScanScreen() {
  const [facing, setFacing] = useState('back');
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const [barcode, setBarcode] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  if (!permission) {
    return <View />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.container}>
        <Text style={styles.message}>We need your camera permission to scan barcodes</Text>
        <Button onPress={requestPermission} title="Grant permission" />
      </View>
    );
  }

  const handleBarcodeScanned = async ({ data }: { data: string }) => {
    if (scanned) return;
    setScanned(true);
    router.push(`/product/${data}`);
  };

  const handleBarcodeSubmit = async () => {
    if (barcode.trim()) {
      router.push(`/product/${barcode.trim()}`);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const results = await api.searchProducts(searchQuery);
      if (results.products && results.products.length > 0) {
        router.push(`/product/${results.products[0].id}`);
      }
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Scan</Text>
      
      <CameraView
        style={styles.camera}
        facing={facing}
        onBarcodeScanned={scanned ? undefined : handleBarcodeScanned}
        barcodeTypes={['ean13', 'ean8', 'upc_a', 'upc_e']}
      >
        <View style={styles.overlay}>
          <Text style={styles.overlayText}>Point at a barcode</Text>
        </View>
      </CameraView>

      <View style={styles.controls}>
        <TouchableOpacity
          style={styles.button}
          onPress={() => setScanned(false)}
        >
          <Text style={styles.buttonText}>{scanned ? 'Scan Again' : 'Camera Active'}</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.manual}>
        <Text style={styles.label}>Enter barcode</Text>
        <TextInput
          style={styles.input}
          placeholder="3017620422003"
          value={barcode}
          onChangeText={setBarcode}
          keyboardType="numeric"
        />
        <TouchableOpacity style={styles.primaryButton} onPress={handleBarcodeSubmit}>
          <Text style={styles.buttonText}>Go</Text>
        </TouchableOpacity>

        <Text style={styles.label}>Search by name</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. yaourt grec"
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        <TouchableOpacity style={styles.primaryButton} onPress={handleSearch} disabled={loading}>
          <Text style={styles.buttonText}>{loading ? 'Searching...' : 'Search'}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  camera: {
    height: 300,
    borderRadius: 14,
    overflow: 'hidden',
    marginBottom: 16,
  },
  overlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.3)',
  },
  overlayText: {
    color: '#fff',
    fontSize: 18,
  },
  controls: {
    marginBottom: 20,
  },
  button: {
    backgroundColor: '#e4e9e5',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  primaryButton: {
    backgroundColor: '#1f9d55',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  manual: {
    gap: 12,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
  },
  input: {
    borderWidth: 1,
    borderColor: '#e4e9e5',
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
  },
  message: {
    textAlign: 'center',
    marginBottom: 16,
  },
});
