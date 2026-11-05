// The shopper's currency follows their country (set by the profile store): euros in France, dollars in the United States.
let usd = false;
export const setMoneyCountry = (country?: string | null) => { usd = country === 'US'; };
export const currencySymbol = () => (usd ? '$' : '€');
/** Cents -> '1,90 €' (France) or '$1.90' (United States). */
export const formatMoney = (cents: number): string => (usd ? '$' + (cents / 100).toFixed(2) : (cents / 100).toFixed(2).replace('.', ',') + ' €');
/** Strings are written with euros; a US shopper sees dollars. */
export const localizeMoney = (s: string): string => (usd ? s.replace(/€/g, '$') : s);
