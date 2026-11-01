import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image } from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { api, formatNutrient } from '@shared';
import type { Product, FitAssessment } from '@shared';

export default function ProductScreen() {
  const { barcode } = useLocalSearchParams<{ barcode: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [fit, setFit] = useState<FitAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadProduct = async () => {
      if (!barcode) return;

      setLoading(true);
      setError('');

      try {
        const data = await api.getProduct(barcode);
        setProduct(data.product);
        setFit(data.fit || []);
      } catch (err) {
        setError('Failed to load product');
      } finally {
        setLoading(false);
      }
    };

    loadProduct();
  }, [barcode]);

  if (loading) {
    return (
      <View style={styles.container}>
        <Text style={styles.text}>Loading...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Product not found</Text>
        <Text style={styles.text}>{error}</Text>
        <TouchableOpacity style={styles.button} onPress={() => router.back()}>
          <Text style={styles.buttonText}>Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!product) {
    return (
      <View style={styles.container}>
        <Text style={styles.text}>No product data</Text>
      </View>
    );
  }

  const nutriColors = {
    a: '#038141',
    b: '#85bb2f',
    c: '#fecb02',
    d: '#ee8100',
    e: '#e63e11',
  };

  return (
    <ScrollView style={styles.container}>
      <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
        <Text style={styles.backText}>← Back</Text>
      </TouchableOpacity>

      <Text style={styles.title}>{product.name}</Text>
      <Text style={styles.subtitle}>{product.brand} • {product.quantityText}</Text>

      {product.imageUrl && (
        <Image source={{ uri: product.imageUrl }} style={styles.image} />
      )}

      {product.nutriScore && (
        <View style={[styles.nutriBadge, { backgroundColor: nutriColors[product.nutriScore as keyof typeof nutriColors] }]}>
          <Text style={styles.nutriText}>Nutri-Score {product.nutriScore.toUpperCase()}</Text>
        </View>
      )}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Nutrition (per 100 g)</Text>
        <NutrientRow label="Energy" value={product.nutriments.energyKcal100g} unit="kcal" />
        <NutrientRow label="Fat" value={product.nutriments.fat100g} unit="g" />
        <NutrientRow label="Saturated fat" value={product.nutriments.saturatedFat100g} unit="g" />
        <NutrientRow label="Carbohydrates" value={product.nutriments.carbohydrates100g} unit="g" />
        <NutrientRow label="Sugars" value={product.nutriments.sugars100g} unit="g" />
        <NutrientRow label="Protein" value={product.nutriments.protein100g} unit="g" />
        <NutrientRow label="Fiber" value={product.nutriments.fiber100g} unit="g" />
        <NutrientRow label="Salt" value={product.nutriments.salt100g} unit="g" />
      </View>

      {product.ingredientsText && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Ingredients</Text>
          <Text style={styles.text}>{product.ingredientsText}</Text>
        </View>
      )}

      {product.allergens.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Allergens</Text>
          <View style={styles.chips}>
            {product.allergens.map((a) => (
              <View key={a} style={styles.badgeDanger}>
                <Text style={styles.badgeText}>{a}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {fit.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Your preferences</Text>
          {fit.map((f) => (
            <View key={f.priority} style={styles.fitRow}>
              <Text style={styles.text}>{f.priority}</Text>
              <View style={[
                styles.badge,
                f.status === 'conflict' ? styles.badgeDanger : f.status === 'unknown' ? styles.badgeWarning : styles.badgeSuccess
              ]}>
                <Text style={styles.badgeText}>{f.status === 'match' ? '✓' : f.status === 'conflict' ? '✕' : '?'} {f.text}</Text>
              </View>
            </View>
          ))}
        </View>
      )}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Actions</Text>
        <TouchableOpacity style={styles.primaryButton} onPress={() => router.push(`/alternatives/${barcode}`)}>
          <Text style={styles.buttonText}>Find Better Alternatives</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.button} onPress={() => router.push('/compare')}>
          <Text style={styles.buttonText}>Compare Products</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Data Quality</Text>
        <Text style={styles.text}>Source: {product.dataQuality.source}</Text>
        <Text style={styles.text}>Last updated: {product.dataQuality.lastUpdatedAt || 'Unknown'}</Text>
        {!product.dataQuality.nutritionComplete && (
          <Text style={styles.warningText}>Missing nutrients: {product.dataQuality.missingNutrients.join(', ')}</Text>
        )}
      </View>
    </ScrollView>
  );
}

function NutrientRow({ label, value, unit }: { label: string; value: number | null; unit: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.text}>{label}</Text>
      <Text style={styles.text}>{value !== null ? value.toFixed(1) + ' ' + unit : '–'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  backButton: {
    marginBottom: 12,
  },
  backText: {
    fontSize: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
  },
  image: {
    width: 100,
    height: 100,
    borderRadius: 8,
    marginBottom: 12,
  },
  nutriBadge: {
    padding: 8,
    borderRadius: 8,
    alignSelf: 'flex-start',
    marginBottom: 12,
  },
  nutriText: {
    color: '#fff',
    fontWeight: 'bold',
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
    marginBottom: 4,
  },
  warningText: {
    fontSize: 14,
    color: '#c47a00',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  badge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    marginRight: 4,
    marginBottom: 4,
  },
  badgeSuccess: {
    backgroundColor: '#e8f6ee',
  },
  badgeWarning: {
    backgroundColor: '#fff1d6',
  },
  badgeDanger: {
    backgroundColor: '#fde4e1',
  },
  badgeText: {
    fontSize: 12,
  },
  fitRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  button: {
    backgroundColor: '#e4e9e5',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
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
});
