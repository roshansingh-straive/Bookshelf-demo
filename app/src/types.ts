export interface BoundingBox {
  top: number;
  left: number;
  width: number;
  height: number;
  shelf_tier?: number;
}

export interface ShelfItem {
  id: string;
  title: string;
  author: string | null;
  confidence: number;
  box: BoundingBox;
  status: 'matched' | 'misplaced' | 'unexpected';
  status_label: string;
  misplaced_reason?: string | null;
  target_bay_name?: string | null;
  sku?: string | null;
  price?: number;
}

export interface PlanogramItem {
  sku: string;
  title: string;
  author: string | null;
  assigned_bay_id: string;
  price: number;
  sales_velocity_units_per_day: number;
  simulated_on_hand: number;
  system_status: string;
  physically_on_shelf: boolean;
  days_since_stockout?: number;
}

export interface MissingItem {
  sku: string;
  title: string;
  author: string | null;
  planogram_bay_id: string;
  simulated_on_hand: number;
  price: number;
  sales_velocity: number;
  is_phantom_inventory: boolean;
  reason: string;
  action: string;
}

export interface ActionTask {
  id: string;
  type: 'missing_item' | 'misplaced_item' | 'record_error';
  severity: 'critical' | 'warning' | 'high' | 'medium';
  badge: string;
  title: string;
  author: string | null;
  sku?: string;
  headline: string;
  suggested_action: string;
  system_on_hand?: number;
  shelf_count?: number;
  resolved?: boolean;
}

export interface ScanMetrics {
  planogram_expected_items: number;
  shelf_items_detected: number;
  matched_count: number;
  missing_count: number;
  misplaced_count: number;
  planogram_compliance_pct: number;
}

export interface ScanResult {
  bay_id: string;
  bay_code: string;
  bay_name: string;
  photo_filename: string;
  photo_url: string;
  scanned_at: string;
  model: string;
  effort: string;
  inference_duration_seconds: number;
  tokens_used: number;
  estimated_cost_usd: number;
  metrics: ScanMetrics;
  planogram_items: PlanogramItem[];
  shelf_items: ShelfItem[];
  missing_items: MissingItem[];
  misplaced_items: ShelfItem[];
  action_tasks: ActionTask[];
}

export interface Bay {
  id: string;
  code: string;
  name: string;
  photo?: string;
  aisle: string;
  section: string;
  difficulty?: string;
  scannable?: boolean;
  status: 'healthy' | 'action_needed' | 'unscanned';
  scanned_today?: boolean;
  last_scanned_at?: string;
  open_exceptions?: number;
  sales_at_risk?: number;
  expected_items_count?: number;
  ground_truth_items_count?: number;
  catalogue_skus?: string[];
}

export interface StoreData {
  store_name: string;
  store_id: string;
  description: string;
  disclaimer: string;
  total_bays: number;
  scannable_bays_count: number;
  bays: Bay[];
  catalogue: Record<string, PlanogramItem>;
  initial_inventory: Record<string, number>;
  summary: {
    on_shelf_availability_pct: number;
    open_exceptions_total: number;
    bays_scanned_today: number;
  };
}
