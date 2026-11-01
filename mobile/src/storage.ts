// AsyncStorage is async but shared/storage.ts is synchronous: preload every fiq_ key into memory once, then write through.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { setStorage } from '@shared/storage';

export async function initStorage(): Promise<void> {
  const keys = (await AsyncStorage.getAllKeys()).filter((k) => k.startsWith('fiq_'));
  const mem = new Map<string, string>(keys.length ? ((await AsyncStorage.multiGet(keys)) as [string, string | null][]).filter(([, v]) => v != null).map(([k, v]) => [k, v as string]) : []);
  setStorage({
    getItem: (k) => mem.get(k) ?? null,
    setItem: (k, v) => { mem.set(k, v); void AsyncStorage.setItem(k, v); },
    removeItem: (k) => { mem.delete(k); void AsyncStorage.removeItem(k); },
    keys: () => [...mem.keys()],
  });
}
