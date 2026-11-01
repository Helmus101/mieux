import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image } from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { api } from '@shared';
import type { Alternative } from '@shared';

export default function AlternativesScreen() {
  const { barcode } = useLocalSearchParams<{ barcode: string }>();
  const [alternatives, setAlternatives] = useState<Alternative[]>([]);
  const [loading, setLoading] = useState(true);
  const [priorities, setPriorities] = useState(['protein', 'sugars']);
  const [categoryMode, setCategoryMode] = useState('similar');

  useEffect(() => {
    const loadAlternatives = async () => {
      if (!barcode) return;

      setLoading(true);

      try {
        const data = await api.getAlternatives(barcode, {
          priorities,
          category_mode: categoryMode,
          price_constraint: 'any',
          limit: 5,
        });

        setAlternatives(data.alternatives || []);
      } catch (err) {
        console.error('Failed to load alternatives:', err);
      } finally {
        setLoading(false);
      }
    };

    loadAlternatives();
  }, [barcode, priorities, categoryMode]);

  if (loading) {
    return (
      <View style={styles.container}>
        <Text style={styles.text}>Loading alternatives...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
        <Text style={styles.backText}>← Back</Text>
      </TouchableOpacity>

      <Text style={styles.title}>Alternatives</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Improve by</Text>
        <View style={styles.chips}>
          <Chip
            label="More protein"
            selected={priorities.includes('protein')}
            onPress={() => setPriorities(['protein'])}
          />
          <Chip
            label="Less sugar"
            selected={priorities.includes('sugars')}
            onPress={() => setPriorities(['sugars'])}
          />
          <Chip
            label="More fiber"
            selected={priorities.includes('fiber')}
            onPress={() => setPriorities(['fiber'])}
          />
          <Chip
            label="Less salt"
            selected={priorities.includes('salt')}
            onPress={() => setPriorities(['salt'])}
          />
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Category mode</Text>
        <View style={styles.chips}>
          <Chip
            label="Similar products"
            selected={categoryMode === 'similar'}
            onPress={() => setCategoryMode('similar')}
          />
          <Chip
            label="Any in category"
            selected={categoryMode === 'any'}
            onPress={() => setCategoryMode('any')}
          />
        </View>
      </View>

      {alternatives.length === 0 ? (
        <View style={styles.card}>
          <Text style={styles.text}>No alternatives found. Try changing your criteria.</Text>
        </View>
      ) : (
        alternatives.map((alt, i) => (
          <TouchableOpacity
            key={alt.product_id}
            style={styles.card}
            onPress={() => router.push(`/product/${alt.product_id}`)}
          >
            <View style={styles.row}>
              {alt.product.imageUrl && (
                <Image source={{ uri: alt.product.imageUrl }} style={styles.image} />
              )}
              <View style={styles.productInfo}>
                <Text style={styles.productName}>{alt.product.name}</Text>
                <Text style={styles.brand}>{alt.product.brand}</Text>
              </View>
              {i === 0 && <View style={styles.recommendedBadge}><Text style={styles.badgeText}>Recommended</Text></View>}
            </View>
            <View style={styles.improvements}>
              {alt.improvements.map((imp) => (
                <Text key={imp} style={styles.successText}>✓ {imp}</Text>
              ))}
            </View>
            <View style={styles.tradeoffs}>
              {alt.tradeoffs.map((trade) => (
                <Text key={trade} style={styles.warningText}>⚠ {trade}</Text>
              ))}
            </View>
          </TouchableOpacity>
        ))
      )}
    </ScrollView>
  );
}

function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <TouchableOpacity
      style={[styles.chip, selected && styles.chipSelected]}
      onPress={onPress}
    >
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
    </TouchableOpacity>
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
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: '#e4e9e5',
    marginRight: 4,
    marginBottom: 4,
  },
  chipSelected: {
    backgroundColor: '#1f9d55',
  },
  chipText: {
    fontSize: 12,
  },
  chipTextSelected: {
    color: '#fff',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
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
  recommendedBadge: {
    backgroundColor: '#1f9d55',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 20,
  },
  badgeText: {
    color: '#fff',
    fontSize: 12,
  },
  improvements: {
    marginTop: 8,
  },
  successText: {
    fontSize: 12,
    color: '#1f9d55',
    marginBottom: 2,
  },
  tradeoffs: {
    marginTop: 4,
  },
  warningText: {
    fontSize: 12,
    color: '#c47a00',
    marginBottom: 2,
  },
});
