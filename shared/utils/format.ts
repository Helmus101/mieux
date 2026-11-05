// Shared formatting utilities

import { formatMoney } from './money';

export const formatCents = (cents: number): string => formatMoney(cents);

export const formatNutrient = (value: number | null, unit: string): string => {
  if (value === null) return '–';
  return `${value.toFixed(1)} ${unit}`;
};

export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('fr-FR');
};

export const truncate = (text: string | null, maxLength: number = 100): string => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
};

/** Liquid = sold by volume: pack size in ml, or (size unknown) a beverage category. */
export function isLiquid(p: { quantity?: { unit: string } | null; categories?: string[] } | null | undefined): boolean {
  if (!p) return false;
  if (p.quantity) return p.quantity.unit === 'ml';
  const c = (p.categories ?? []).join(' ');
  return c.includes('beverages') || c.includes('drinks') || c.includes('milks');
}

/** Unit price from a price per 100 g / 100 ml: euros per kg (or per L for liquids), plus the pack price when the pack size is known. */
export function unitPrice(price100Cents: number | null | undefined, quantity?: { amount: number; unit: string } | null, liquidHint = false): { perUnitCents: number; unit: 'kg' | 'L'; packCents: number | null; size: string | null } | null {
  if (price100Cents == null) return null;
  const liquid = quantity ? quantity.unit === 'ml' : liquidHint;
  const pack = quantity?.amount ? Math.round((price100Cents * quantity.amount) / 100) : null;
  const size = quantity?.amount ? (quantity.amount >= 1000 ? `${Math.round(quantity.amount / 100) / 10} ${liquid ? 'L' : 'kg'}` : `${Math.round(quantity.amount)} ${liquid ? 'ml' : 'g'}`) : null;
  return { perUnitCents: Math.round(price100Cents * 10), unit: liquid ? 'L' : 'kg', packCents: pack, size };
}
