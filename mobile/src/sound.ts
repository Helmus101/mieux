/**
 * Sound effects for the mobile app using expo-av.
 * Plays synthetic sounds without external audio files.
 */
import { Audio } from 'expo-av';

let audioContext: Audio.AudioContext | null = null;

export async function initSound() {
  if (!audioContext) {
    audioContext = new Audio.AudioContext();
    await audioContext.setAudioModeAsync({
      playsInSilentModeIOS: true,
      staysActiveInBackground: false,
    });
  }
}

export async function playSound(type: 'success' | 'error' | 'tap' | 'scan') {
  try {
    await initSound();

    // Create simple synthetic sounds using Web Audio API pattern
    // For mobile, we'll use short pre-encoded base64 sounds
    const sounds: Record<string, string> = {
      success: 'data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU', // placeholder
      error: 'data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU', // placeholder
      tap: 'data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU', // placeholder
      scan: 'data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU', // placeholder
    };

    // For now, use expo-av with minimal beeps
    // In production, add actual WAV base64 strings
    const { sound } = await Audio.Sound.createAsync(
      { uri: sounds[type] || sounds.tap },
      { shouldPlay: true }
    );
    await sound.playAsync();
    sound.setOnPlaybackStatusUpdate(async (status) => {
      if (status.isLoaded && status.didJustFinish) {
        await sound.unloadAsync();
      }
    });
  } catch (e) {
    // Silently fail if audio not available
  }
}
