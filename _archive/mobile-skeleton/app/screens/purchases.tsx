import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { api, formatCents, formatDate } from '@shared';
import type { Receipt, Purchase } from '@shared';

export default function PurchasesScreen() {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [totalSpending, setTotalSpending] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [receiptsData, purchasesData] = await Promise.all([api.getReceipts(), api.getPurchases()]);
        setReceipts(receiptsData.receipts);
        setPurchases(purchasesData.purchases);
        setTotalSpending(purchasesData.recorded_spending_cents);
      } catch (err) {
        console.error('Failed to load purchases:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const deleteReceipt = async (id: number) => {
    try {
      await api.deleteReceipt(id);
      const [receiptsData, purchasesData] = await Promise.all([api.getReceipts(), api.getPurchases()]);
      setReceipts(receiptsData.receipts);
      setPurchases(purchasesData.purchases);
      setTotalSpending(purchasesData.recorded_spending_cents);
    } catch (err) {
      console.error('Failed to delete receipt:', err);
      alert('Failed to delete receipt');
    }
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <Text style={styles.text}>Loading purchases...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Purchases</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>This month</Text>
        <Text style={styles.totalAmount}>{formatCents(totalSpending)}</Text>
        <Text style={styles.text}>
          Recorded grocery spending · {receipts.length} receipt{receipts.length === 1 ? '' : 's'}
        </Text>
      </View>

      <View style={styles.card}>
        <View style={styles.row}>
          <Text style={styles.cardTitle}>Receipts</Text>
          <TouchableOpacity onPress={() => router.push('/receipt/capture')}>
            <Text style={styles.addText}>+ Scan Receipt</Text>
          </TouchableOpacity>
        </View>
        {receipts.length === 0 ? (
          <Text style={styles.text}>No receipts yet</Text>
        ) : (
          receipts.map((r) => (
            <View key={r.id} style={styles.itemRow}>
              <View style={styles.itemInfo}>
                <Text style={styles.itemName}>{r.retailer}</Text>
                <Text style={styles.itemDetail}>{formatDate(r.purchase_date)}</Text>
              </View>
              <View style={styles.itemActions}>
                <Text style={styles.itemAmount}>{formatCents(r.total_cents)}</Text>
                <TouchableOpacity onPress={() => deleteReceipt(r.id)}>
                  <Text style={styles.deleteText}>Delete</Text>
                </TouchableOpacity>
              </View>
            </View>
          ))
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Purchase History</Text>
        {purchases.length === 0 ? (
          <Text style={styles.text}>No purchases yet</Text>
        ) : (
          purchases.map((p) => (
            <View key={p.key} style={styles.itemRow}>
              <View style={styles.itemInfo}>
                <Text style={styles.itemName}>{p.name}</Text>
                <Text style={styles.itemDetail}>{p.times}x purchased</Text>
              </View>
              <View style={styles.itemActions}>
                <Text style={styles.itemAmount}>{formatCents(p.last_price_cents)}</Text>
                {p.product_id && (
                  <TouchableOpacity onPress={() => router.push(`/product/${p.product_id}`)}>
                    <Text style={styles.viewText}>View</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          ))
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Data Export</Text>
        <TouchableOpacity style={styles.button} onPress={() => router.push('/profile')}>
          <Text style={styles.buttonText}>Manage your data in Profile</Text>
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
  totalAmount: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  addText: {
    color: '#1f9d55',
    fontWeight: 'bold',
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
  itemActions: {
    alignItems: 'flex-end',
  },
  itemAmount: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  deleteText: {
    color: '#c0392b',
    fontSize: 12,
  },
  viewText: {
    color: '#1f9d55',
    fontSize: 12,
  },
  button: {
    backgroundColor: '#e4e9e5',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  buttonText: {
    color: '#666',
    fontWeight: '600',
  },
});
