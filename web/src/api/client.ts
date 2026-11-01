import axios, { AxiosInstance } from 'axios';
import type {
  Receipt,
  Purchase,
  UserPreferences,
  AuthResponse,
  LoginRequest,
  RegisterRequest,
} from '../types';

const API_BASE = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8010/v1';

export class MieuxAPI {
  private client: AxiosInstance;
  private token: string | null = null;
  private sessionId: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      } else if (this.sessionId) {
        config.headers['X-Session-Id'] = this.sessionId;
      }
      return config;
    });
  }

  setToken(token: string) {
    this.token = token;
  }

  setSessionId(sessionId: string) {
    this.sessionId = sessionId;
  }

  clearAuth() {
    this.token = null;
    this.sessionId = null;
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
  async getProduct(barcode: string) {
    const response = await this.client.get(`/products/${barcode}`);
    return response.data;
  }

  async searchProducts(query: string) {
    const response = await this.client.get('/search', { params: { q: query } });
    return response.data;
  }

  async getAlternatives(barcode: string, request: any) {
    const response = await this.client.post(`/products/${barcode}/alternatives`, request);
    return response.data;
  }

  async compareProducts(productIds: string[]) {
    const response = await this.client.post('/comparisons', { product_ids: productIds });
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
