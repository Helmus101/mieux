import { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { api, formatCents } from '@shared';
import type { ParsedReceipt } from '@shared';

export default function ReceiptReviewScreen() {
  const params = useLocalSearchParams();
  const [receipt, setReceipt] = useState<ParsedReceipt | null>(null);
  const [loading, setLoading] = useState(false);

  // For now, create a placeholder receipt
  // TODO: Implement ML Kit Vision OCR and use actual parsed data
  useEffect(() => {
    if (params.imageUri) {
      setReceipt({
        retailer: 'Monoprix',
        purchase_date: new Date().toISOString().split('T')[0],
        total_cents: 1153,
        items: [
          {
            raw: 'YAOURT GREC',
            quantity: 1,
            unit_price_cents: 159,
            line_total_cents: 159,
            is_discount: false,
            extraction_confidence: 0.95,
            match_candidate: null,
          },
          {
            raw: 'BANANES',
            quantity: 1,
            unit_price_cents: 210,
            line_total_cents: 210,
            is_discount: false,
            extraction_confidence: 0.95,
            match_candidate: null,
          },
        ],
        warnings: [],
        status: 'preview',
      });
    }
  }, [params]);

  const handleConfirm = async () => {
    if (!receipt) return;

    setLoading(true);
    try {
      const items = receipt.items.map((item) => ({
        raw_description: item.raw,
        quantity: item.quantity,
        unit_price_cents: item.unit_price_cents,
        line_total_cents: item.line_total_cents,
        is_discount: item.is_discount,
        matched_product_id: item.match_candidate?.product_id || null,
        extraction_confidence: item.extraction_confidence,
        match_confidence: item.match_candidate?.score || null,
      }));

      const result = await api.confirmReceipt({
        retailer: receipt.retailer,
        purchase_date: receipt.purchase_date,
        total_cents: receipt.total_cents,
        items,
        allow_duplicate: false,
      });

      alert('Receipt saved!');
      router.push('/purchases');
    } catch (err) {
      console.error('Failed to save receipt:', err);
      alert('Failed to save receipt');
    } finally {
      setLoading(false);
    }
  };

  if (!receipt) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Review Receipt</Text>
        <Text style={styles.text}>No receipt data. Please scan a receipt first.</Text>
        <TouchableOpacity style={styles.button} onPress={() => router.push('/receipt/capture')}>
          <Text style={styles.buttonText}>Scan Receipt</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Review Receipt</Text>

      <View style={styles.card}>
        <View style={styles.row}>
          <Text style={styles.label}>Store:</Text>
          <Text style={styles.value}>{receipt.retailer || 'Unknown'}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Date:</Text>
          <Text style={styles.value}>{receipt.purchase_date || 'Unknown'}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Total:</Text>
          <Text style={styles.value}>{formatCents(receipt.total_cents || 0)}</Text>
        </View>
        {receipt.warnings.length > 0 && (
          <View style={styles.warnings}>
            {receipt.warnings.map((w, i) => (
              <Text key={i} style={styles.warningText}>⚠ {w}</Text>
            ))}
          </View>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Items</Text>
        {receipt.items.map((item, i) => (
          <View key={i} style={styles.itemRow}>
            <View style={styles.itemInfo}>
              <Text style={styles.itemName}>{item.raw}</Text>
              <Text style={styles.itemDetail}>Qty: {item.quantity} • {formatCents(item.unit_price_cents)}</Text>
            </View>
            <Text style={styles.itemTotal}>{formatCents(item.line_total_cents)}</Text>
          </View>
        ))}
      </View>

      <View style={styles.actions}>
        <TouchableOpacity style={styles.cancelButton} onPress={() => router.back()}>
          <Text style={styles.cancelText}>Cancel</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.primaryButton}
          onPress={handleConfirm}
          disabled={loading}
        >
          <Text style={styles.buttonText}>{loading ? 'Saving...' : 'Confirm Receipt'}</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  text: {
    fontSize: 14,
    marginBottom: 16,
  },
  card: {
    backgroundColor: '#f7faf8',
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
  },
  cardTitle: {
    fontSize: 17,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  label: {
    fontSize: 14,
    color: '#666',
  },
  value: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  warnings: {
    marginTop: 12,
  },
  warningText: {
    fontSize: 14,
    color: '#c47a00',
    marginBottom: 4,
  },
  itemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#e4e9e5',
  },
  itemInfo: {
    flex: 1,
  },
  itemName: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  itemDetail: {
    fontSize: 12,
    color: '#666',
  },
  itemTotal: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  actions: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 10,
  },
  cancelButton: {
    flex: 1,
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
    backgroundColor: '#e4e9e5',
  },
  cancelText: {
    color: '#666',
    fontWeight: '600',
  },
  primaryButton: {
    flex: 1,
    backgroundColor: '#1f9d55',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
});
