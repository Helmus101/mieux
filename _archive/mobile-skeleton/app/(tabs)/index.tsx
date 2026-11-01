import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image } from 'react-native';
import { router } from 'expo-router';
import { api, formatCents } from '@shared';
import type { Product } from '@shared';

export default function HomeScreen() {
  const [scans, setScans] = useState<Product[]>([]);
  const [monthlySpending, setMonthlySpending] = useState(0);
  const [receiptCount, setReceiptCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [scansData, purchasesData] = await Promise.all([api.getScans(), api.getPurchases()]);
        const recentScans = scansData.scans.slice(0, 5).map((s: any) => s.product);
        setScans(recentScans);
        setMonthlySpending(purchasesData.recorded_spending_cents);
        setReceiptCount(purchasesData.purchases.length);
      } catch (err) {
        console.error('Failed to load home data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.subtitle}>YOUR FOOD DECISIONS, MADE CLEARER</Text>
      <Text style={styles.title}>What are you buying today?</Text>
      <Text style={styles.text}>Scan a product to understand it and compare your options.</Text>

      <TouchableOpacity style={styles.primaryButton} onPress={() => router.push('/scan')}>
        <Text style={styles.buttonText}>Scan a Product</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.button} onPress={() => router.push('/receipt/capture')}>
        <Text style={styles.buttonText}>Scan Receipt</Text>
        <Text style={styles.subtext}>Track purchases and the prices you pay</Text>
      </TouchableOpacity>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>This month</Text>
        <Text style={styles.totalAmount}>{formatCents(monthlySpending)}</Text>
        <Text style={styles.text}>
          Recorded grocery spending · {receiptCount} receipt{receiptCount === 1 ? '' : 's'}
        </Text>
      </View>

      <Text style={styles.sectionTitle}>Recent scans</Text>
      {scans.length === 0 ? (
        <Text style={styles.text}>Nothing scanned yet. Try 3017620422003.</Text>
      ) : (
        scans.map((p) => (
          <TouchableOpacity
            key={p.id}
            style={styles.card}
            onPress={() => router.push(`/product/${p.id}`)}
          >
            <View style={styles.row}>
              {p.imageUrl && <Image source={{ uri: p.imageUrl }} style={styles.image} />}
              <View style={styles.productInfo}>
                <Text style={styles.productName}>{p.name}</Text>
                <Text style={styles.brand}>{p.brand}</Text>
              </View>
              {p.nutriScore && (
                <View style={[styles.nutriBadge, { backgroundColor: { a: '#038141', b: '#85bb2f', c: '#fecb02', d: '#ee8100', e: '#e63e11' }[p.nutriScore] }]}>
                  <Text style={styles.nutriText}>{p.nutriScore.toUpperCase()}</Text>
                </View>
              )}
            </View>
          </TouchableOpacity>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  subtitle: {
    fontSize: 12,
    letterSpacing: 0.08,
    color: '#666',
    marginBottom: 4,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginVertical: 4,
  },
  text: {
    fontSize: 16,
    color: '#666',
    marginBottom: 16,
  },
  primaryButton: {
    backgroundColor: '#1f9d55',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 10,
  },
  button: {
    backgroundColor: '#e4e9e5',
    padding: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 14,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 18,
  },
  subtext: {
    color: '#666',
    fontSize: 12,
    marginTop: 4,
  },
  card: {
    backgroundColor: '#f7faf8',
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
  },
  cardLabel: {
    fontSize: 12,
    color: '#666',
  },
  totalAmount: {
    fontSize: 28,
    fontWeight: 'bold',
    marginVertical: 4,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  image: {
    width: 52,
    height: 52,
    borderRadius: 8,
    marginRight: 10,
  },
  productInfo: {
    flex: 1,
  },
  productName: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  brand: {
    fontSize: 12,
    color: '#666',
  },
  nutriBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 20,
  },
  nutriText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 12,
  },
});
