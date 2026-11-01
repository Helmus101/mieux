/** EAN-13 / EAN-8 / UPC-A check digit: rejects most mis-reads so the first valid hit can be trusted. Platform-free. */
export function validBarcode(c: string): boolean {
  if (!/^\d{8}$|^\d{12,13}$/.test(c)) return false;
  const d = c.split('').map(Number), chk = d.pop()!;
  const sum = d.reverse().reduce((a, x, i) => a + x * (i % 2 === 0 ? 3 : 1), 0);
  return (10 - (sum % 10)) % 10 === chk;
}
