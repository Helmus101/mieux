import { View, Text, StyleSheet } from 'react-native';

export default function CompareScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Compare</Text>
      <Text>Product comparison coming soon...</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
});
