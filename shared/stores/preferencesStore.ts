import { create } from 'zustand';
import { api } from '../api/client';
import type { UserPreferences } from '../types';

interface PreferencesState extends UserPreferences {
  isLoading: boolean;
  error: string | null;
  setPreferences: (prefs: UserPreferences) => void;
  updateDiet: (diet: string) => void;
  updatePriorities: (priorities: string[]) => void;
  updateAllergens: (allergens: string[]) => void;
  fetchPreferences: () => Promise<void>;
  savePreferences: () => Promise<void>;
}

export const usePreferencesStore = create<PreferencesState>((set, get) => ({
  diet: 'omnivore',
  priorities: ['protein', 'sugars'],
  allergens: [],
  isLoading: false,
  error: null,

  setPreferences: (prefs) => set(prefs),

  updateDiet: (diet) => set({ diet }),

  updatePriorities: (priorities) => set({ priorities }),

  updateAllergens: (allergens) => set({ allergens }),

  fetchPreferences: async () => {
    set({ isLoading: true, error: null });
    try {
      const prefs = await api.getPreferences();
      set({ ...prefs, isLoading: false });
    } catch (error) {
      set({ error: 'Failed to fetch preferences', isLoading: false });
    }
  },

  savePreferences: async () => {
    set({ isLoading: true, error: null });
    try {
      const { diet, priorities, allergens } = get();
      await api.updatePreferences({ diet, priorities, allergens });
      set({ isLoading: false });
    } catch (error) {
      set({ error: 'Failed to save preferences', isLoading: false });
    }
  },
}));
