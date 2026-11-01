import { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput } from 'react-native';
import { router } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';

export default function ReceiptCaptureScreen() {
  const [processing, setProcessing] = useState(false);

  const handleImageUpload = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        aspect: [4, 3],
        quality: 1,
      });

      if (!result.canceled) {
        // For now, navigate to review with placeholder data
        // TODO: Implement ML Kit Vision OCR
        router.push('/receipt/review', {
          params: { imageUri: result.assets[0].uri }
        });
      }
    } catch (err) {
      console.error('Image picker failed:', err);
      alert('Failed to select image');
    }
  };

  const handleCameraCapture = async () => {
    try {
      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: true,
        aspect: [4, 3],
        quality: 1,
      });

      if (!result.canceled) {
        // TODO: Implement ML Kit Vision OCR
        router.push('/receipt/review', {
          params: { imageUri: result.assets[0].uri }
        });
      }
    } catch (err) {
      console.error('Camera failed:', err);
      alert('Failed to capture image');
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Scan Receipt</Text>
      <Text style={styles.text}>Upload a receipt image to scan</Text>

      <TouchableOpacity style={styles.primaryButton} onPress={handleCameraCapture}>
        <Text style={styles.buttonText}>Take Photo</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.button} onPress={handleImageUpload}>
        <Text style={styles.buttonText}>Select from Gallery</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.cancelButton} onPress={() => router.back()}>
        <Text style={styles.cancelText}>Cancel</Text>
      </TouchableOpacity>

      <View style={styles.infoCard}>
        <Text style={styles.infoTitle}>Coming Soon</Text>
        <Text style={styles.infoText}>
          On-device OCR with ML Kit Vision will automatically extract:
        </Text>
        <Text style={styles.infoText}>• Store name and date</Text>
        <Text style={styles.infoText}>• Line items and prices</Text>
        <Text style={styles.infoText}>• Total amount</Text>
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
    marginBottom: 8,
  },
  text: {
    fontSize: 14,
    color: '#666',
    marginBottom: 20,
  },
  primaryButton: {
    backgroundColor: '#1f9d55',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 12,
  },
  button: {
    backgroundColor: '#e4e9e5',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 12,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  cancelButton: {
    padding: 12,
    alignItems: 'center',
  },
  cancelText: {
    color: '#666',
  },
  infoCard: {
    backgroundColor: '#f7faf8',
    borderRadius: 14,
    padding: 14,
    marginTop: 20,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
});
