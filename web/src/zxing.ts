// Slim ZXing entry: only the UPC/EAN readers the app scans, instead of the whole multi-format bundle
// (QR, PDF417, Aztec, DataMatrix, Code 39/93/128…), which roughly halves the decoder download.
// Loaded on demand by the scanner, so none of it is part of the first page load.
import BinaryBitmap from '@zxing/library/esm/core/BinaryBitmap';
import HybridBinarizer from '@zxing/library/esm/core/common/HybridBinarizer';
import MultiFormatUPCEANReader from '@zxing/library/esm/core/oned/MultiFormatUPCEANReader';
import { HTMLCanvasElementLuminanceSource } from '@zxing/library/esm/browser/HTMLCanvasElementLuminanceSource';

export { BinaryBitmap, HybridBinarizer, MultiFormatUPCEANReader, HTMLCanvasElementLuminanceSource };

/** Decode the UPC/EAN barcode in a canvas. Throws when there is no valid code in the frame. */
export function decodeCanvas(reader: MultiFormatUPCEANReader, canvas: HTMLCanvasElement): string {
  const bitmap = new BinaryBitmap(new HybridBinarizer(new HTMLCanvasElementLuminanceSource(canvas)));
  return reader.decode(bitmap).getText();
}
