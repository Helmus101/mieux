// Shared TypeScript types for Mieux

export interface Product {
  id: string;
  barcode: string;
  name: string;
  brand: string | null;
  category: string | null;
  categories: string[];
  imageUrl: string | null;
  quantityText: string | null;
  nutriments: Nutriments;
  ingredientsText: string | null;
  allergens: string[];
  traces: string[];
  additives: string[];
  analysis: string[];
  nutriScore: string | null;
  nutriScoreVersion: string | null;
  dataQuality: DataQuality;
}

export interface Nutriments {
  energyKcal100g: number | null;
  fat100g: number | null;
  saturatedFat100g: number | null;
  carbohydrates100g: number | null;
  sugars100g: number | null;
  protein100g: number | null;
  fiber100g: number | null;
  salt100g: number | null;
}

export interface DataQuality {
  nutritionComplete: boolean;
  missingNutrients: string[];
  ingredientsAvailable: boolean;
  allergensAvailable: boolean;
  productImageAvailable: boolean;
  nutriScoreAvailable: boolean;
  source: string;
  lastUpdatedAt: string | null;
}

export interface FitAssessment {
  priority: string;
  status: 'match' | 'partial' | 'no_match' | 'conflict' | 'unknown';
  text: string;
}

export interface Alternative {
  product_id: string;
  product: Product;
  comparison: Record<string, number>;
  improvements: string[];
  tradeoffs: string[];
  similarity: number;
  data_quality: string;
}

export interface ReceiptItem {
  raw: string;
  quantity: number;
  unit_price_cents: number;
  line_total_cents: number;
  is_discount: boolean;
  extraction_confidence: number;
  match_candidate: MatchCandidate | null;
}

export interface MatchCandidate {
  product_id: string;
  name: string;
  score: number;
}

export interface ParsedReceipt {
  retailer: string | null;
  purchase_date: string | null;
  total_cents: number | null;
  items: ReceiptItem[];
  warnings: string[];
  possible_duplicate: boolean;
  status: string;
}

export interface UserPreferences {
  diet: string;
  priorities: string[];
  allergens: string[];
}

export interface Receipt {
  id: number;
  retailer: string;
  purchase_date: string;
  total_cents: number;
  lines: number;
}

export interface Purchase {
  key: string;
  name: string;
  product_id: string | null;
  times: number;
  history: PurchaseHistory[];
  last_price_cents: number;
}

export interface PurchaseHistory {
  date: string;
  retailer: string;
  unit_price_cents: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}
