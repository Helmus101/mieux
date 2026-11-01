// On-device receipt OCR. Expo Go has no text-recognition module, so this returns a clear "not available" result and the screen falls back
// to pasting text. To enable it, build a development client (`npx expo prebuild`) and implement recognize() with Google ML Kit
// (Android/iOS, e.g. a config-plugin package) or Apple Vision; send only the recognised LINES to /v1/receipts/preview, never the image.
export interface OcrResult { text: string | null; reason?: string }
export async function recognizeReceipt(): Promise<OcrResult> {
  return { text: null, reason: 'La lecture automatique du ticket demande une version de développement avec ML Kit / Apple Vision. En attendant, collez le texte du ticket ci-dessous.' };
}
