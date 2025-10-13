/**
 * TypeScript type definitions for API endpoints and responses.
 *
 * These types define the shape of data returned from API endpoints,
 * providing compile-time safety for API interactions.
 */

import { AxiosResponse } from 'axios';
import {
  Roommate, RoommateCreate, RoommateUpdate,
  Chore, ChoreCreate, ChoreUpdate,
  Assignment, SubChoreProgress,
  ShoppingItem, ShoppingItemCreate, ShoppingItemUpdate, PurchaseData, ShoppingListMetadata,
  Request, RequestCreate, ApprovalData, RequestMetadata,
  LaundrySlot, LaundrySlotCreate, LaundrySlotUpdate, LaundryCompletionData, LaundryMetadata,
  BlockedTimeSlot, BlockedTimeSlotCreate, BlockedTimeSlotUpdate,
  CalendarConfig, CalendarEvent, GoogleCalendar, CalendarSyncStatus,
  User, AuthStatus, GoogleLoginData,
  ApplicationState, HealthCheck,
  SubChore
} from './models';

// ============================================================================
// Generic API Response Wrappers
// ============================================================================

export type ApiPromise<T> = Promise<AxiosResponse<T>>;

// ============================================================================
// Chores API Types
// ============================================================================

export interface ChoreAPI {
  getAll: () => ApiPromise<Chore[]>;
  create: (chore: ChoreCreate) => ApiPromise<Chore>;
  update: (id: number, chore: ChoreUpdate) => ApiPromise<Chore>;
  delete: (id: number) => ApiPromise<void>;
}

// ============================================================================
// Sub-Chores API Types
// ============================================================================

export interface SubChoreAPI {
  getAll: (choreId: number, config?: any) => ApiPromise<SubChore[]>;
  create: (choreId: number, subChore: { name: string }) => ApiPromise<SubChore>;
  update: (choreId: number, subChoreId: number, subChore: { name: string }) => ApiPromise<SubChore>;
  delete: (choreId: number, subChoreId: number) => ApiPromise<void>;
  toggle: (choreId: number, subChoreId: number, assignmentIndex?: number | null) => ApiPromise<{ sub_chore_id: number; completed: boolean }>;
  getProgress: (choreId: number, assignmentIndex?: number | null) => ApiPromise<SubChoreProgress>;
}

// ============================================================================
// Shopping List API Types
// ============================================================================

export interface ShoppingListAPI {
  getAll: (status?: string | null) => ApiPromise<ShoppingItem[]>;
  create: (item: ShoppingItemCreate) => ApiPromise<ShoppingItem>;
  update: (id: number, item: ShoppingItemUpdate) => ApiPromise<ShoppingItem>;
  delete: (id: number) => ApiPromise<void>;
  markPurchased: (id: number, purchaseData: PurchaseData) => ApiPromise<ShoppingItem>;
  getHistory: (days?: number) => ApiPromise<ShoppingItem[]>;
  getMetadata: () => ApiPromise<ShoppingListMetadata>;
  clearAllHistory: () => ApiPromise<{ cleared_count: number }>;
  clearHistoryFromDate: (fromDate: string) => ApiPromise<{ cleared_count: number }>;
}

// ============================================================================
// Request API Types
// ============================================================================

export interface RequestAPI {
  getAll: (status?: string | null) => ApiPromise<Request[]>;
  create: (request: RequestCreate) => ApiPromise<Request>;
  update: (id: number, request: Partial<Request>) => ApiPromise<Request>;
  delete: (id: number) => ApiPromise<void>;
  approve: (id: number, approvalData: ApprovalData) => ApiPromise<Request>;
  getPendingForUser: (userId: number) => ApiPromise<Request[]>;
  getMetadata: () => ApiPromise<RequestMetadata>;
}

// ============================================================================
// Roommates API Types
// ============================================================================

export interface RoommateAPI {
  getAll: () => ApiPromise<Roommate[]>;
  create: (roommate: RoommateCreate) => ApiPromise<Roommate>;
  update: (id: number, roommate: RoommateUpdate) => ApiPromise<Roommate>;
  delete: (id: number) => ApiPromise<void>;
}

// ============================================================================
// Assignments API Types
// ============================================================================

export interface AssignmentAPI {
  assignChores: () => ApiPromise<{ assignments: Assignment[]; message: string }>;
  getCurrent: () => ApiPromise<Assignment[]>;
  resetCycle: () => ApiPromise<{ message: string }>;
}

// ============================================================================
// Laundry API Types
// ============================================================================

export interface LaundryQueryParams {
  date?: string;
  roommate_id?: number;
  status?: string;
}

export interface LaundryAPI {
  getAll: (params?: LaundryQueryParams) => ApiPromise<LaundrySlot[]>;
  create: (slot: LaundrySlotCreate) => ApiPromise<LaundrySlot>;
  update: (id: number, slot: LaundrySlotUpdate) => ApiPromise<LaundrySlot>;
  delete: (id: number) => ApiPromise<void>;
  complete: (id: number, completionData?: LaundryCompletionData) => ApiPromise<LaundrySlot>;
  checkConflicts: (conflictData: {
    date: string;
    time_slot: string;
    machine_type: string;
    exclude_slot_id?: number;
  }) => ApiPromise<{ conflicts: LaundrySlot[] }>;
  getMetadata: () => ApiPromise<LaundryMetadata>;
}

// ============================================================================
// Calendar API Types
// ============================================================================

export interface CalendarAPI {
  getStatus: () => ApiPromise<{ enabled: boolean; has_credentials: boolean }>;
  setupCredentials: (credentials: any) => ApiPromise<{ success: boolean }>;
  getOAuthUrl: () => ApiPromise<{ oauth_url: string }>;
  getCalendarList: () => ApiPromise<GoogleCalendar[]>;
  getConfig: () => ApiPromise<CalendarConfig>;
  saveConfig: (config: CalendarConfig) => ApiPromise<CalendarConfig>;
  createEvent: (eventData: Partial<CalendarEvent>) => ApiPromise<CalendarEvent>;
  deleteEvent: (calendarId: string, eventId: string) => ApiPromise<void>;
}

// ============================================================================
// Authentication API Types
// ============================================================================

export interface AuthAPI {
  getStatus: () => ApiPromise<AuthStatus>;
  initiateGoogleLogin: (redirectUri: string) => ApiPromise<{ auth_url: string }>;
  getProfile: () => ApiPromise<{ user: User }>;
  refreshSession: () => ApiPromise<{ success: boolean }>;
  linkRoommate: (roommateId: number) => ApiPromise<{ success: boolean; roommate: Roommate }>;
  unlinkRoommate: () => ApiPromise<{ success: boolean }>;
  logout: () => ApiPromise<{ success: boolean }>;
  revokeAccess: () => ApiPromise<{ success: boolean }>;
  setupCredentials: (credentials: any) => ApiPromise<{ success: boolean }>;
}

// ============================================================================
// User Calendar API Types
// ============================================================================

export interface UserCalendarAPI {
  getConfig: () => ApiPromise<CalendarConfig>;
  saveConfig: (config: CalendarConfig) => ApiPromise<CalendarConfig>;
  getCalendars: () => ApiPromise<GoogleCalendar[]>;
  syncChores: () => ApiPromise<{ synced_count: number; events: CalendarEvent[] }>;
  getSyncStatus: () => ApiPromise<CalendarSyncStatus>;
}

// ============================================================================
// Blocked Time Slots API Types
// ============================================================================

export interface BlockedTimeSlotsAPI {
  getAll: (params?: { date?: string }) => ApiPromise<BlockedTimeSlot[]>;
  create: (data: BlockedTimeSlotCreate) => ApiPromise<BlockedTimeSlot>;
  update: (id: number, data: BlockedTimeSlotUpdate) => ApiPromise<BlockedTimeSlot>;
  delete: (id: number) => ApiPromise<void>;
  checkConflicts: (data: {
    date: string;
    time_slot: string;
    exclude_slot_id?: number;
  }) => ApiPromise<{ conflicts: BlockedTimeSlot[] }>;
}

// ============================================================================
// Application State API Types
// ============================================================================

export interface StateAPI {
  get: () => ApiPromise<ApplicationState>;
  health: () => ApiPromise<HealthCheck>;
}

// ============================================================================
// Complete API Interface
// ============================================================================

export interface RoomieRosterAPI {
  chores: ChoreAPI;
  subChores: SubChoreAPI;
  shoppingList: ShoppingListAPI;
  requests: RequestAPI;
  roommates: RoommateAPI;
  assignments: AssignmentAPI;
  laundry: LaundryAPI;
  calendar: CalendarAPI;
  auth: AuthAPI;
  userCalendar: UserCalendarAPI;
  blockedTimeSlots: BlockedTimeSlotsAPI;
  state: StateAPI;
}
