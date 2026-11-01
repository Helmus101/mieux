import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput } from 'react-native';
import { router } from 'expo-router';
import { useAuthStore, usePreferencesStore, api } from '@shared';
import type { UserPreferences } from '@shared';

export default function ProfileScreen() {
  const { token, user, logout, login, register } = useAuthStore();
  const { diet, priorities, allergens, updateDiet, updatePriorities, updateAllergens, fetchPreferences, savePreferences } = usePreferencesStore();
  const [showAuth, setShowAuth] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');

  useEffect(() => {
    if (token) {
      fetchPreferences();
    }
  }, [token]);

  const handleAuth = async () => {
    setAuthError('');

    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password);
      }
      setShowAuth(false);
      setEmail('');
      setPassword('');
    } catch (err) {
      setAuthError((err as Error).message);
    }
  };

  const handleSavePreferences = async () => {
    await savePreferences();
    alert('Preferences saved!');
  };

  const handleExport = async () => {
    try {
      const data = await api.exportData();
      const json = JSON.stringify(data, null, 2);
      alert('Data exported! (File save not implemented yet)');
    } catch (err) {
      console.error('Export failed:', err);
      alert('Failed to export data');
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm('Are you sure you want to delete your account? This cannot be undone.')) return;

    try {
      await api.deleteAccount();
      logout();
      alert('Account deleted');
      router.push('/');
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete account');
    }
  };

  const toggleAllergen = (allergen: string) => {
    if (allergens.includes(allergen)) {
      updateAllergens(allergens.filter((a) => a !== allergen));
    } else {
      updateAllergens([...allergens, allergen]);
    }
  };

  const togglePriority = (priority: string) => {
    if (priorities.includes(priority)) {
      updatePriorities(priorities.filter((p) => p !== priority));
    } else {
      updatePriorities([...priorities, priority]);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Profile</Text>

      {!token ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Authentication</Text>
          <Text style={styles.text}>Create an account to sync your data across devices</Text>
          <TouchableOpacity style={styles.primaryButton} onPress={() => setShowAuth(true)}>
            <Text style={styles.buttonText}>Sign In / Register</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.card}>
          <View style={styles.row}>
            <View>
              <Text style={styles.cardTitle}>Signed in as</Text>
              <Text style={styles.text}>{user?.id}</Text>
            </View>
            <TouchableOpacity style={styles.button} onPress={logout}>
              <Text style={styles.buttonText}>Sign Out</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {showAuth && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>{isLogin ? 'Sign In' : 'Register'}</Text>
          <TextInput
            style={styles.input}
            placeholder="Email"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
          />
          <TextInput
            style={styles.input}
            placeholder="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />
          {authError && <Text style={styles.errorText}>{authError}</Text>}
          <TouchableOpacity style={styles.primaryButton} onPress={handleAuth}>
            <Text style={styles.buttonText}>{isLogin ? 'Sign In' : 'Register'}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.linkButton} onPress={() => setIsLogin(!isLogin)}>
            <Text style={styles.linkText}>
              {isLogin ? 'Need an account? Register' : 'Have an account? Sign In'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.linkButton} onPress={() => setShowAuth(false)}>
            <Text style={styles.linkText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      )}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Dietary Preferences</Text>
        <Text style={styles.label}>Diet</Text>
        <View style={styles.chips}>
          <Chip label="Omnivore" selected={diet === 'omnivore'} onPress={() => updateDiet('omnivore')} />
          <Chip label="Vegetarian" selected={diet === 'vegetarian'} onPress={() => updateDiet('vegetarian')} />
          <Chip label="Vegan" selected={diet === 'vegan'} onPress={() => updateDiet('vegan')} />
        </View>
        <TouchableOpacity style={styles.primaryButton} onPress={handleSavePreferences}>
          <Text style={styles.buttonText}>Save Preferences</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Priorities</Text>
        <View style={styles.chips}>
          {['protein', 'sugars', 'fiber', 'salt', 'saturated_fat'].map((p) => (
            <Chip key={p} label={p} selected={priorities.includes(p)} onPress={() => togglePriority(p)} />
          ))}
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Allergens</Text>
        <View style={styles.chips}>
          {['gluten', 'crustaceans', 'eggs', 'fish', 'peanuts', 'soybeans', 'milk', 'nuts', 'celery', 'mustard', 'sesame', 'sulphites', 'lupin', 'molluscs'].map((a) => (
            <Chip key={a} label={a} selected={allergens.includes(a)} onPress={() => toggleAllergen(a)} />
          ))}
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Data Management</Text>
        <TouchableOpacity style={styles.button} onPress={handleExport}>
          <Text style={styles.buttonText}>Export Data</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.dangerButton} onPress={handleDeleteAccount}>
          <Text style={styles.dangerText}>Delete Account</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>About</Text>
        <Text style={styles.text}>FoodIQ v1.0.0</Text>
        <Text style={styles.text}>Helps you make smarter food choices</Text>
      </View>
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
    marginBottom: 4,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  primaryButton: {
    backgroundColor: '#1f9d55',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
  },
  button: {
    backgroundColor: '#e4e9e5',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  input: {
    borderWidth: 1,
    borderColor: '#e4e9e5',
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    marginBottom: 8,
  },
  errorText: {
    color: '#c0392b',
    fontSize: 14,
    marginBottom: 8,
  },
  linkButton: {
    padding: 8,
    alignItems: 'center',
  },
  linkText: {
    color: '#1f9d55',
    fontSize: 14,
  },
  label: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 8,
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
  dangerButton: {
    backgroundColor: '#fde4e1',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
  },
  dangerText: {
    color: '#c0392b',
    fontWeight: '600',
  },
});
