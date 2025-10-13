/**
 * TypeScript type definitions for RoomieRoster data models.
 *
 * These types match the backend Python models and provide compile-time
 * type safety for the frontend application.
 */

// ============================================================================
// Roommate Types
// ============================================================================

export interface Roommate {
  id: number;
  name: string;
  current_cycle_points: number;
  google_id?: string | null;
  google_profile_picture_url?: string | null;
  linked_at?: string | null;  // ISO 8601 datetime string
}

export interface RoommateCreate {
  name: string;
  current_cycle_points?: number;
}

export interface RoommateUpdate {
  name?: string;
  current_cycle_points?: number;
  google_id?: string | null;
  google_profile_picture_url?: string | null;
}

// ============================================================================
// Chore Types
// ============================================================================

export type ChoreFrequency = 'daily' | 'weekly' | 'biweekly' | 'monthly';
export type ChoreType = 'predefined' | 'random';

export interface SubChore {
  id: number;
  name: string;
  completed: boolean;
}

export interface Chore {
  id: number;
  name: string;
  frequency: ChoreFrequency;
  type: ChoreType;
  points: number;
  sub_chores?: SubChore[];
}

export interface ChoreCreate {
  name: string;
  frequency: ChoreFrequency;
  type: ChoreType;
  points: number;
  sub_chores?: Array<{ name: string }>;
}

export interface ChoreUpdate {
  name?: string;
  frequency?: ChoreFrequency;
  type?: ChoreType;
  points?: number;
  sub_chores?: SubChore[];
}

// ============================================================================
// Assignment Types
// ============================================================================

export interface Assignment {
  chore_id: number;
  chore_name: string;
  roommate_id: number;
  roommate_name: string;
  assigned_date: string;  // ISO 8601 date
  due_date: string;       // ISO 8601 date
  frequency: ChoreFrequency;
  type: ChoreType;
  points: number;
  sub_chore_completions?: Record<string, boolean>;
}

export interface SubChoreProgress {
  total_sub_chores: number;
  completed_sub_chores: number;
  completion_percentage: number;
  sub_chore_statuses: Record<string, boolean>;
}

// ============================================================================
// Shopping List Types
// ============================================================================

export type ShoppingItemStatus = 'active' | 'purchased';

export interface ShoppingItem {
  id: number;
  item_name: string;
  estimated_price?: number | null;
  actual_price?: number | null;
  brand_preference?: string;
  notes?: string;
  added_by: number;
  added_by_name: string;
  status: ShoppingItemStatus;
  date_added: string;  // ISO 8601 datetime
  purchased_by?: number | null;
  purchased_by_name?: string | null;
  purchase_date?: string | null;  // ISO 8601 datetime
}

export interface ShoppingItemCreate {
  item_name: string;
  estimated_price?: number;
  brand_preference?: string;
  notes?: string;
  added_by: number;
  added_by_name: string;
}

export interface ShoppingItemUpdate {
  item_name?: string;
  estimated_price?: number;
  brand_preference?: string;
  notes?: string;
  status?: ShoppingItemStatus;
}

export interface PurchaseData {
  purchased_by: number;
  purchased_by_name: string;
  actual_price?: number;
  notes?: string;
}

export interface ShoppingListMetadata {
  last_modified: string;
  total_items: number;
  active_items: number;
  purchased_items: number;
  timestamp: string;
}

// ============================================================================
// Request Types
// ============================================================================

export type RequestStatus = 'pending' | 'approved' | 'declined' | 'auto-approved';

export interface RequestApproval {
  approved_by: number;
  approved_by_name: string;
  approval_status: 'approved' | 'declined';
  approval_date: string;  // ISO 8601 datetime
  notes?: string;
}

export interface Request {
  id: number;
  item_name: string;
  estimated_price?: number;
  brand_preference?: string;
  notes?: string;
  requested_by: number;
  requested_by_name: string;
  request_date: string;  // ISO 8601 datetime
  status: RequestStatus;
  approval_threshold: number;
  auto_approve_under: number;
  approvals: RequestApproval[];
  final_decision_date?: string | null;
  final_decision_by?: number | null;
  final_decision_by_name?: string | null;
}

export interface RequestCreate {
  item_name: string;
  estimated_price?: number;
  brand_preference?: string;
  notes?: string;
  requested_by: number;
  requested_by_name: string;
  approval_threshold?: number;
  auto_approve_under?: number;
}

export interface ApprovalData {
  approved_by: number;
  approved_by_name: string;
  approval_status: 'approved' | 'declined';
  notes?: string;
}

export interface RequestMetadata {
  last_modified: string;
  total_requests: number;
  pending_requests: number;
  approved_requests: number;
  declined_requests: number;
  auto_approved_requests: number;
  timestamp: string;
}

// ============================================================================
// Laundry Scheduling Types
// ============================================================================

export type LaundryStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
export type MachineType = 'washer' | 'dryer' | 'combo';
export type LoadType = 'lights' | 'darks' | 'delicates' | 'towels' | 'bedding' | 'mixed';

export interface LaundrySlot {
  id: number;
  roommate_id: number;
  roommate_name: string;
  date: string;  // YYYY-MM-DD format
  time_slot: string;  // e.g., "09:00-11:00"
  machine_type: MachineType;
  load_type: LoadType;
  estimated_loads: number;
  actual_loads?: number;
  status: LaundryStatus;
  notes?: string;
  created_at: string;  // ISO 8601 datetime
  completed_date?: string | null;
}

export interface LaundrySlotCreate {
  roommate_id: number;
  roommate_name: string;
  date: string;
  time_slot: string;
  machine_type: MachineType;
  load_type: LoadType;
  estimated_loads: number;
  notes?: string;
}

export interface LaundrySlotUpdate {
  date?: string;
  time_slot?: string;
  machine_type?: MachineType;
  load_type?: LoadType;
  estimated_loads?: number;
  status?: LaundryStatus;
  notes?: string;
}

export interface LaundryCompletionData {
  actual_loads?: number;
  notes?: string;
}

export interface LaundryConflictCheck {
  date: string;
  time_slot: string;
  machine_type: MachineType;
  exclude_slot_id?: number;
}

export interface LaundryMetadata {
  last_modified: string;
  total_slots: number;
  scheduled_slots: number;
  in_progress_slots: number;
  completed_slots: number;
  cancelled_slots: number;
  timestamp: string;
}

// ============================================================================
// Blocked Time Slots Types
// ============================================================================

export interface BlockedTimeSlot {
  id: number;
  date: string;  // YYYY-MM-DD format
  time_slot: string;  // e.g., "09:00-11:00"
  reason: string;
  created_by: string;
  created_at: string;  // ISO 8601 datetime
  sync_to_calendar: boolean;
}

export interface BlockedTimeSlotCreate {
  date: string;
  time_slot: string;
  reason: string;
  created_by: string;
  sync_to_calendar?: boolean;
}

export interface BlockedTimeSlotUpdate {
  date?: string;
  time_slot?: string;
  reason?: string;
  sync_to_calendar?: boolean;
}

export interface BlockedTimeConflictCheck {
  date: string;
  time_slot: string;
  exclude_slot_id?: number;
}

// ============================================================================
// Calendar Types
// ============================================================================

export interface CalendarConfig {
  calendar_id?: string;
  enabled: boolean;
  sync_assignments: boolean;
  event_color?: string;
  reminder_minutes?: number;
}

export interface CalendarEvent {
  id: string;
  summary: string;
  description?: string;
  start: string;  // ISO 8601 datetime
  end: string;    // ISO 8601 datetime
  calendar_id: string;
}

export interface GoogleCalendar {
  id: string;
  summary: string;
  description?: string;
  primary: boolean;
}

export interface CalendarSyncStatus {
  last_sync: string | null;
  sync_count: number;
  errors: string[];
}

// ============================================================================
// Authentication Types
// ============================================================================

export interface User {
  google_id: string;
  email: string;
  name: string;
  picture?: string;
  linked_roommate_id?: number | null;
  linked_roommate_name?: string | null;
  csrf_token?: string;
}

export interface AuthStatus {
  authenticated: boolean;
  user?: User;
}

export interface GoogleLoginData {
  redirect_uri: string;
}

export interface OAuthCredentials {
  access_token: string;
  refresh_token?: string;
  token_uri: string;
  client_id: string;
  client_secret: string;
  scopes: string[];
}

// ============================================================================
// Application State Types
// ============================================================================

export interface ApplicationState {
  last_run_date: string | null;
  predefined_chore_states: Record<string, number>;
  current_assignments: Assignment[];
  global_predefined_rotation?: number;
}

export interface HealthCheck {
  status: string;
  database: {
    connected: boolean;
    type: 'postgresql' | 'json';
  };
  timestamp: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  error?: string;
}

export interface ApiError {
  error: string;
  message?: string;
  details?: any;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// ============================================================================
// Form Data Types
// ============================================================================

export interface ChoreFormData {
  name: string;
  frequency: ChoreFrequency;
  type: ChoreType;
  points: number;
}

export interface RoommateFormData {
  name: string;
}

export interface ShoppingItemFormData {
  item_name: string;
  estimated_price: string | number;
  brand_preference: string;
  notes: string;
}

export interface LaundrySlotFormData {
  date: string;
  time_slot: string;
  machine_type: MachineType;
  load_type: LoadType;
  estimated_loads: number;
  notes: string;
}

// ============================================================================
// UI State Types
// ============================================================================

export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

export interface NotificationState {
  show: boolean;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
}

// ============================================================================
// Utility Types
// ============================================================================

export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;
export type ID = number | string;

// Type guard helpers
export const isChore = (obj: any): obj is Chore => {
  return obj && typeof obj.id === 'number' && typeof obj.name === 'string';
};

export const isRoommate = (obj: any): obj is Roommate => {
  return obj && typeof obj.id === 'number' && typeof obj.name === 'string';
};

export const isShoppingItem = (obj: any): obj is ShoppingItem => {
  return obj && typeof obj.id === 'number' && typeof obj.item_name === 'string';
};
