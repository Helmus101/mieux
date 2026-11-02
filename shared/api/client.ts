import axios, { AxiosInstance } from 'axios';
import { getLocale, t } from '../i18n';
import { getApiBase, getStrict } from '../config';
import { load, save } from '../storage';
import type {
  Receipt,
  Purchase,
  UserPreferences,
  AuthResponse,
  LoginRequest,
  RegisterRequest,
} from '../types';


export interface IdentityInput { name: string | null; city: string | null; postcode: string | null; platform: string | null }
export interface Identity extends IdentityInput { first_seen: string | null; last_seen: string | null }

export class MieuxAPI {
  private client: AxiosInstance;
  private token: string | null = null;
  private sessionId: string | null = null;
  private prefsHeader: string | null = null;

  // Anonymous session so scanning works without an account; persisted through the platform storage adapter.
  private static anonymousSession(): string {
    let id = load<string | null>('fiq_session_id', null);
    if (!id) { id = 'anon-' + Math.random().toString(36).slice(2) + Date.now().toString(36); save('fiq_session_id', id); }
    return id;
  }

  constructor() {
    this.client = axios.create({
      timeout: 25000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.request.use((config) => {
      config.baseURL = getApiBase();
      config.headers['X-Lang'] = getLocale();
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
        if (this.prefsHeader) config.headers['X-Prefs'] = this.prefsHeader;  // a signed-in account stores nothing: restrictions travel with each request
      } else {
        this.sessionId = this.sessionId ?? MieuxAPI.anonymousSession();
        config.headers['X-Session-Id'] = this.sessionId;
      }
      return config;
    });

    // The local server can be restarting or briefly busy: retry a few times before giving up, then say so in plain words instead of "Network Error".
    this.client.interceptors.response.use(undefined, async (error) => {
      const cfg = error?.config;
      if (error?.response || !cfg) throw error;
      cfg.__retries = (cfg.__retries ?? 0) + 1;
      if (cfg.__retries <= 3) {
        await new Promise((r) => setTimeout(r, 600 * cfg.__retries));
        return this.client.request(cfg);
      }
      error.message = t('net.down');
      throw error;
    });
  }

  setToken(token: string) {
    this.token = token;
  }

  clearToken() {
    this.token = null;
  }

  setPrefs(prefs: { diet: string; priorities: string[]; allergens: string[] }) {
    this.prefsHeader = encodeURIComponent(JSON.stringify(prefs));
  }

  setSessionId(sessionId: string) {
    this.sessionId = sessionId;
  }

  clearAuth() {
    this.token = null;
    this.sessionId = MieuxAPI.anonymousSession();
  }

  // Auth endpoints
  async login(data: LoginRequest): Promise<AuthResponse> {
    const response = await this.client.post('/auth/login', data);
    return response.data;
  }

  async register(data: RegisterRequest): Promise<AuthResponse> {
    const response = await this.client.post('/auth/register', data);
    return response.data;
  }

  // Product endpoints
  async getProduct(barcode: string, approximate = false) {
    const response = await this.client.get(`/products/${barcode}`, { params: { approximate, strict: getStrict() } });
    return response.data;
  }

  async searchProducts(query: string) {
    const response = await this.client.get('/search', { params: { q: query } });
    return response.data;
  }

  async storePrices(barcode: string, lat: number, lon: number, radius_km = 25) {
    const response = await this.client.post(`/products/${barcode}/store-prices`, { lat, lon, radius_km });
    return response.data;
  }

  async retailers(barcode: string, lat: number, lon: number, radius_km = 15, chains: string[] = []) {
    const response = await this.client.post(`/products/${barcode}/retailers`, { lat, lon, radius_km, chains });
    return response.data;
  }

  async confirmListing(barcode: string, chain_id: string) {
    const response = await this.client.post(`/products/${barcode}/listings`, { chain_id });
    return response.data;
  }

  async substitutionVerdict(barcode: string, alt_id: string, verdict: 'ok' | 'not_comparable') {
    const response = await this.client.post(`/products/${barcode}/substitutions`, { alt_id, verdict });
    return response.data;
  }

  async contribute(barcode: string, data: Record<string, unknown>) {
    const response = await this.client.post(`/products/${barcode}/contribute`, data);
    return response.data;
  }

  async clearContribution(barcode: string) {
    const response = await this.client.delete(`/products/${barcode}/contribute`);
    return response.data;
  }

  async getAlternatives(barcode: string, request: any) {
    const response = await this.client.post(`/products/${barcode}/alternatives`, { ...request, strict_additives: getStrict() });
    return response.data;
  }

  async compareProducts(productIds: string[], approximate = false) {
    const response = await this.client.post('/comparisons', { product_ids: productIds, approximate });
    return response.data;
  }

  // Scan endpoints
  async addScan(barcode: string) {
    const response = await this.client.post('/scans', { barcode });
    return response.data;
  }

  async getScans() {
    const response = await this.client.get('/scans');
    return response.data;
  }

  // Receipt endpoints
  async previewReceipt(lines: any[]) {
    const response = await this.client.post('/receipts/preview', { lines });
    return response.data;
  }

  async confirmReceipt(receipt: any) {
    const response = await this.client.post('/receipts/confirm', receipt);
    return response.data;
  }

  async getReceipts(): Promise<{ receipts: Receipt[] }> {
    const response = await this.client.get('/receipts');
    return response.data;
  }

  async deleteReceipt(id: number) {
    const response = await this.client.delete(`/receipts/${id}`);
    return response.data;
  }

  async getPurchases(): Promise<{ purchases: Purchase[]; recorded_spending_cents: number; note: string }> {
    const response = await this.client.get('/purchases');
    return response.data;
  }

  async getStorePrices(barcode: string, loc: { lat: number; lon: number; radius_km: number }) {
    const response = await this.client.post(`/products/${barcode}/store-prices`, loc);
    return response.data;
  }

  async geocode(postcode: string) {
    const response = await this.client.post('/geocode', { postcode });
    return response.data;
  }

  async addPrice(barcode: string, priceCents: number) {
    const response = await this.client.post(`/products/${barcode}/prices`, { price_cents: priceCents });
    return response.data;
  }

  async deletePrice(id: number) {
    const response = await this.client.delete(`/prices/${id}`);
    return response.data;
  }

  async explain(originalId: string, altId: string) {
    const response = await this.client.post('/explain', { original_id: originalId, alt_id: altId });
    return response.data;
  }

  async getBudget() {
    const response = await this.client.get('/budget');
    return response.data;
  }

  async putBudget(cfg: { period: string; amount_cents: number; style: string; savings_goal_cents: number | null; categories?: Record<string, number> }) {
    const response = await this.client.put('/me/budget', cfg);
    return response.data;
  }

  async deleteBudget() {
    const response = await this.client.delete('/me/budget');
    return response.data;
  }

  async chooseSaving(body: { original_id: string; alt_id: string; expected_saving_cents: number; original_per100_cents: number | null }) {
    const response = await this.client.post('/savings/choose', body);
    return response.data;
  }

  async getInsights() {
    const response = await this.client.get('/insights');
    return response.data;
  }

  // Who is using the app: first name and city, saved without an account so the profile is not lost
  // with the browser storage. Nothing else leaves the device through this endpoint.
  async getIdentity(): Promise<Identity> {
    const response = await this.client.get('/me/profile');
    return response.data;
  }

  async putIdentity(p: IdentityInput) {
    const response = await this.client.put('/me/profile', p);
    return response.data;
  }

  // Preferences endpoints
  async getPreferences(): Promise<UserPreferences> {
    const response = await this.client.get('/me/preferences');
    return response.data;
  }

  async updatePreferences(prefs: UserPreferences) {
    const response = await this.client.put('/me/preferences', prefs);
    return response.data;
  }

  // User data endpoints
  async exportData() {
    const response = await this.client.get('/me/export');
    return response.data;
  }

  async deleteAccount() {
    const response = await this.client.delete('/me');
    return response.data;
  }
}

export const api = new MieuxAPI();
