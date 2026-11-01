// Central haptics. Every feel goes through here so it can be switched off in Profile (stored on the device).
import * as H from 'expo-haptics';
import { load, save } from '@shared/storage';

let on = true;
export const initHaptics = () => { on = load<boolean>('fiq_haptics', true); };
export const hapticsEnabled = () => on;
export const setHapticsEnabled = (v: boolean) => { on = v; save('fiq_haptics', v); if (v) light(); };

const run = (f: () => Promise<void>) => { if (on) void f().catch(() => undefined); };
export const select = () => run(() => H.selectionAsync());                                              // toggles, segmented, tabs
export const light = () => run(() => H.impactAsync(H.ImpactFeedbackStyle.Light));                       // list rows
export const medium = () => run(() => H.impactAsync(H.ImpactFeedbackStyle.Medium));                     // primary buttons
export const heavy = () => run(() => H.impactAsync(H.ImpactFeedbackStyle.Heavy));                       // destructive confirmations
export const success = () => run(() => H.notificationAsync(H.NotificationFeedbackType.Success));        // barcode read, receipt saved, saving chosen
export const warning = () => run(() => H.notificationAsync(H.NotificationFeedbackType.Warning));        // allergen conflict, duplicate, over budget
export const error = () => run(() => H.notificationAsync(H.NotificationFeedbackType.Error));            // failures
