import { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput } from 'react-native';
import { router } from 'expo-router';
import { api } from '@shared';
import type { Product } from '@shared';

export default function CompareScreen() {
  const [products, setProducts] = useState<Product[]>([]);
  const [barcode, setBarcode] = useState('');
  const [comparison, setComparison] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const addProduct = async () => {
    if (!barcode.trim() || products.length >= 4) return;

    setLoading(true);
    try {
      const data = await api.getProduct(barcode.trim());
      setProducts([...products, data.product]);
      setBarcode('');
    } catch (err) {
      console.error('Failed to load product:', err);
    } finally {
      setLoading(false);
    }
  };

  const compare = async () => {
    if (products.length < 2) return;

    setLoading(true);
    try {
      const data = await api.compareProducts(products.map((p) => p.id));
      setComparison(data);
    } catch (err) {
      console.error('Failed to compare:', err);
    } finally {
      setLoading(false);
    }
  };

  const removeProduct = (id: string) => {
    setProducts(products.filter((p) => p.id !== id));
    setComparison(null);
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Compare Products</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Add products to compare</Text>
        <View style={styles.row}>
          <TextInput
            style={styles.input}
            placeholder="Enter barcode"
            value={barcode}
            onChangeText={setBarcode}
          />
          <TouchableOpacity
            style={[styles.button, products.length >= 4 && styles.buttonDisabled]}
            onPress={addProduct}
            disabled={loading || products.length >= 4}
          >
            <Text style={styles.buttonText}>Add</Text>
          </TouchableOpacity>
        </View>
        <Text style={styles.text}>{products.length}/4 products selected</Text>
      </View>

      {products.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Selected products</Text>
          {products.map((p) => (
            <View key={p.id} style={styles.row}>
              <View style={styles.productInfo}>
                <Text style={styles.productName}>{p.name}</Text>
              </View>
              <TouchableOpacity onPress={() => removeProduct(p.id)}>
                <Text style={styles.removeText}>Remove</Text>
              </TouchableOpacity>
            </View>
          ))}
          <TouchableOpacity
            style={styles.primaryButton}
            onPress={compare}
            disabled={loading}
          >
            <Text style={styles.buttonText}>{loading ? 'Comparing...' : 'Compare'}</Text>
          </TouchableOpacity>
        </View>
      )}

      {comparison && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Comparison</Text>
          <Text style={styles.text}>{comparison.basis}</Text>
          <ComparisonTable products={products} comparison={comparison} />
          <Text style={[styles.text, { marginTop: 12 }]}>{comparison.note}</Text>
        </View>
      )}
    </ScrollView>
  );
}

function ComparisonTable({ products, comparison }: { products: Product[]; comparison: any }) {
  return (
    <View style={styles.table}>
      <View style={styles.tableHeader}>
        <Text style={styles.tableCell}>Nutrient</Text>
        {products.map((p) => (
          <Text key={p.id} style={styles.tableCell}>{p.name}</Text>
        ))}
      </View>
      {comparison.rows.map((row: any) => (
        <View key={row.field} style={styles.tableRow}>
          <Text style={styles.tableCell}>{row.field}</Text>
          {row.values.map((v: any, i: number) => (
            <Text
              key={i}
              style={[styles.tableCell, row.favourable[i] && styles.tableCellBest]}
            >
              {v !== null ? v.toFixed(1) : '–'}
            </Text>
          ))}
        </View>
      ))}
    </View>
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
  text: {
    fontSize: 14,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#e4e9e5',
    borderRadius: 10,
    padding: 10,
    fontSize: 16,
    marginRight: 8,
  },
  button: {
    backgroundColor: '#1f9d55',
    padding: 10,
    borderRadius: 10,
    alignItems: 'center',
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  primaryButton: {
    backgroundColor: '#1f9d55',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 12,
  },
  productInfo: {
    flex: 1,
  },
  productName: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  removeText: {
    color: '#c0392b',
    marginLeft: 8,
  },
  table: {
    marginTop: 12,
  },
  tableHeader: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#e4e9e5',
    paddingBottom: 6,
  },
  tableRow: {
    flexDirection: 'row',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#e4e9e5',
  },
  tableCell: {
    flex: 1,
    fontSize: 14,
  },
  tableCellBest: {
    backgroundColor: '#e8f6ee',
    fontWeight: 'bold',
  },
});
