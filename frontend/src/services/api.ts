/**
 * TypeScript API Service Module
 *
 * This is the TypeScript version of api.js, providing fully typed API interactions
 * with compile-time safety and better IDE support.
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type {
  // Data Models
  Chore, ChoreCreate, ChoreUpdate,
  Roommate, RoommateCreate, RoommateUpdate,
  Assignment,
  ShoppingItem, ShoppingItemCreate, ShoppingItemUpdate, PurchaseData, ShoppingListMetadata,
  Request, RequestCreate, ApprovalData, RequestMetadata,
  LaundrySlot, LaundrySlotCreate, LaundrySlotUpdate, LaundryCompletionData, LaundryMetadata,
  BlockedTimeSlot, BlockedTimeSlotCreate, BlockedTimeSlotUpdate,
  CalendarConfig, GoogleCalendar, CalendarEvent, CalendarSyncStatus,
  User, AuthStatus,
  ApplicationState, HealthCheck,
  SubChore, SubChoreProgress,

  // API Types
  ChoreAPI, SubChoreAPI, ShoppingListAPI, RequestAPI, RoommateAPI,
  AssignmentAPI, LaundryAPI, LaundryQueryParams, CalendarAPI, AuthAPI,
  UserCalendarAPI, BlockedTimeSlotsAPI, StateAPI
} from '../types';

// ============================================================================
// Axios Instance Configuration
// ============================================================================

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Include cookies for CSRF tokens
});

// ============================================================================
// CSRF Token Management
// ============================================================================

let csrfToken: string | null = null;

const getCSRFToken = async (): Promise<string | null> => {
  if (!csrfToken) {
    try {
      const response = await api.get<{ user: User }>('/auth/profile');
      if (response.data?.user?.csrf_token) {
        csrfToken = response.data.user.csrf_token;
      }
    } catch (error) {
      // CSRF token not available (user not logged in)
      console.log('CSRF token not available');
    }
  }
  return csrfToken;
};

// ============================================================================
// Request Interceptor
// ============================================================================

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig): Promise<InternalAxiosRequestConfig> => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);

    // Add CSRF token for non-GET requests
    if (config.method && config.method.toLowerCase() !== 'get') {
      const token = await getCSRFToken();
      if (token && config.headers) {
        config.headers['X-CSRF-Token'] = token;
      }
    }

    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// ============================================================================
// Response Interceptor
// ============================================================================

api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message);

    // Clear CSRF token on auth errors to force refresh
    if (error.response?.status === 403 || error.response?.status === 401) {
      csrfToken = null;
    }

    return Promise.reject(error);
  }
);

// ============================================================================
// Export function to clear tokens (for logout)
// ============================================================================

export const clearTokens = (): void => {
  csrfToken = null;
};

// ============================================================================
// Chores API
// ============================================================================

export const choreAPI: ChoreAPI = {
  getAll: () => api.get<Chore[]>('/chores'),
  create: (chore: ChoreCreate) => api.post<Chore>('/chores', chore),
  update: (id: number, chore: ChoreUpdate) => api.put<Chore>(`/chores/${id}`, chore),
  delete: (id: number) => api.delete<void>(`/chores/${id}`),
};

// ============================================================================
// Sub-chores API
// ============================================================================

export const subChoreAPI: SubChoreAPI = {
  getAll: (choreId: number, config: AxiosRequestConfig = {}) =>
    api.get<SubChore[]>(`/chores/${choreId}/sub-chores`, config),
  create: (choreId: number, subChore: { name: string }) =>
    api.post<SubChore>(`/chores/${choreId}/sub-chores`, subChore),
  update: (choreId: number, subChoreId: number, subChore: { name: string }) =>
    api.put<SubChore>(`/chores/${choreId}/sub-chores/${subChoreId}`, subChore),
  delete: (choreId: number, subChoreId: number) =>
    api.delete<void>(`/chores/${choreId}/sub-chores/${subChoreId}`),
  toggle: (choreId: number, subChoreId: number, assignmentIndex: number | null = null) =>
    api.post<{ sub_chore_id: number; completed: boolean }>(
      `/chores/${choreId}/sub-chores/${subChoreId}/toggle`,
      { assignment_index: assignmentIndex }
    ),
  getProgress: (choreId: number, assignmentIndex: number | null = null) =>
    api.get<SubChoreProgress>(
      `/chores/${choreId}/progress${assignmentIndex !== null ? `?assignment_index=${assignmentIndex}` : ''}`
    ),
};

// ============================================================================
// Shopping List API
// ============================================================================

export const shoppingListAPI: ShoppingListAPI = {
  getAll: (status: string | null = null) =>
    api.get<ShoppingItem[]>(`/shopping-list${status ? `?status=${status}` : ''}`),
  create: (item: ShoppingItemCreate) => api.post<ShoppingItem>('/shopping-list', item),
  update: (id: number, item: ShoppingItemUpdate) => api.put<ShoppingItem>(`/shopping-list/${id}`, item),
  delete: (id: number) => api.delete<void>(`/shopping-list/${id}`),
  markPurchased: (id: number, purchaseData: PurchaseData) =>
    api.post<ShoppingItem>(`/shopping-list/${id}/purchase`, purchaseData),
  getHistory: (days: number = 30) => api.get<ShoppingItem[]>(`/shopping-list/history?days=${days}`),
  getMetadata: () => api.get<ShoppingListMetadata>('/shopping-list/metadata'),
  clearAllHistory: () => api.post<{ cleared_count: number }>('/shopping-list/clear-all-history'),
  clearHistoryFromDate: (fromDate: string) =>
    api.post<{ cleared_count: number }>('/shopping-list/clear-history-from-date', { from_date: fromDate }),
};

// ============================================================================
// Request API
// ============================================================================

export const requestAPI: RequestAPI = {
  getAll: (status: string | null = null) =>
    api.get<Request[]>(`/requests${status ? `?status=${status}` : ''}`),
  create: (request: RequestCreate) => api.post<Request>('/requests', request),
  update: (id: number, request: Partial<Request>) => api.put<Request>(`/requests/${id}`, request),
  delete: (id: number) => api.delete<void>(`/requests/${id}`),
  approve: (id: number, approvalData: ApprovalData) =>
    api.post<Request>(`/requests/${id}/approve`, approvalData),
  getPendingForUser: (userId: number) => api.get<Request[]>(`/requests/pending/${userId}`),
  getMetadata: () => api.get<RequestMetadata>('/requests/metadata'),
};

// ============================================================================
// Roommates API
// ============================================================================

export const roommateAPI: RoommateAPI = {
  getAll: () => api.get<Roommate[]>('/roommates'),
  create: (roommate: RoommateCreate) => api.post<Roommate>('/roommates', roommate),
  update: (id: number, roommate: RoommateUpdate) => api.put<Roommate>(`/roommates/${id}`, roommate),
  delete: (id: number) => api.delete<void>(`/roommates/${id}`),
};

// ============================================================================
// Assignments API
// ============================================================================

export const assignmentAPI: AssignmentAPI = {
  assignChores: () => api.post<{ assignments: Assignment[]; message: string }>('/assign-chores'),
  getCurrent: () => api.get<Assignment[]>('/current-assignments'),
  resetCycle: () => api.post<{ message: string }>('/reset-cycle'),
};

// ============================================================================
// Laundry Scheduling API
// ============================================================================

export const laundryAPI: LaundryAPI = {
  getAll: (params: LaundryQueryParams = {}) => {
    const queryParams = new URLSearchParams();
    if (params.date) queryParams.append('date', params.date);
    if (params.roommate_id) queryParams.append('roommate_id', params.roommate_id.toString());
    if (params.status) queryParams.append('status', params.status);

    const queryString = queryParams.toString();
    return api.get<LaundrySlot[]>(`/laundry-slots${queryString ? `?${queryString}` : ''}`);
  },
  create: (slot: LaundrySlotCreate) => api.post<LaundrySlot>('/laundry-slots', slot),
  update: (id: number, slot: LaundrySlotUpdate) => api.put<LaundrySlot>(`/laundry-slots/${id}`, slot),
  delete: (id: number) => api.delete<void>(`/laundry-slots/${id}`),
  complete: (id: number, completionData: LaundryCompletionData = {}) =>
    api.post<LaundrySlot>(`/laundry-slots/${id}/complete`, completionData),
  checkConflicts: (conflictData: {
    date: string;
    time_slot: string;
    machine_type: string;
    exclude_slot_id?: number;
  }) => api.post<{ conflicts: LaundrySlot[] }>('/laundry-slots/check-conflicts', conflictData),
  getMetadata: () => api.get<LaundryMetadata>('/laundry-slots/metadata'),
};

// ============================================================================
// Calendar Integration API
// ============================================================================

export const calendarAPI: CalendarAPI = {
  getStatus: () => api.get<{ enabled: boolean; has_credentials: boolean }>('/calendar/status'),
  setupCredentials: (credentials: any) =>
    api.post<{ success: boolean }>('/calendar/setup-credentials', { credentials }),
  getOAuthUrl: () => api.get<{ oauth_url: string }>('/calendar/oauth-url'),
  getCalendarList: () => api.get<GoogleCalendar[]>('/calendar/calendars'),
  getConfig: () => api.get<CalendarConfig>('/calendar/config'),
  saveConfig: (config: CalendarConfig) => api.post<CalendarConfig>('/calendar/config', config),
  createEvent: (eventData: Partial<CalendarEvent>) =>
    api.post<CalendarEvent>('/calendar/create-event', eventData),
  deleteEvent: (calendarId: string, eventId: string) =>
    api.delete<void>('/calendar/delete-event', {
      data: { calendar_id: calendarId, event_id: eventId }
    }),
};

// ============================================================================
// Authentication API
// ============================================================================

export const authAPI: AuthAPI = {
  getStatus: () => api.get<AuthStatus>('/auth/status'),
  initiateGoogleLogin: (redirectUri: string) =>
    api.post<{ auth_url: string }>('/auth/google-login', { redirect_uri: redirectUri }),
  getProfile: () => api.get<{ user: User }>('/auth/profile'),
  refreshSession: () => api.post<{ success: boolean }>('/auth/refresh'),
  linkRoommate: (roommateId: number) =>
    api.post<{ success: boolean; roommate: Roommate }>('/auth/link-roommate', { roommate_id: roommateId }),
  unlinkRoommate: () => api.post<{ success: boolean }>('/auth/unlink-roommate'),
  logout: () => api.post<{ success: boolean }>('/auth/logout'),
  revokeAccess: () => api.post<{ success: boolean }>('/auth/revoke'),
  setupCredentials: (credentials: any) =>
    api.post<{ success: boolean }>('/auth/setup-credentials', { credentials }),
};

// ============================================================================
// User Calendar API
// ============================================================================

export const userCalendarAPI: UserCalendarAPI = {
  getConfig: () => api.get<CalendarConfig>('/user-calendar/config'),
  saveConfig: (config: CalendarConfig) => api.post<CalendarConfig>('/user-calendar/config', config),
  getCalendars: () => api.get<GoogleCalendar[]>('/user-calendar/calendars'),
  syncChores: () => api.post<{ synced_count: number; events: CalendarEvent[] }>('/user-calendar/sync-chores'),
  getSyncStatus: () => api.get<CalendarSyncStatus>('/user-calendar/sync-status'),
};

// ============================================================================
// Blocked Time Slots API
// ============================================================================

export const blockedTimeSlotsAPI: BlockedTimeSlotsAPI = {
  getAll: (params: { date?: string } = {}) =>
    api.get<BlockedTimeSlot[]>('/blocked-time-slots', { params }),
  create: (data: BlockedTimeSlotCreate) => api.post<BlockedTimeSlot>('/blocked-time-slots', data),
  update: (id: number, data: BlockedTimeSlotUpdate) =>
    api.put<BlockedTimeSlot>(`/blocked-time-slots/${id}`, data),
  delete: (id: number) => api.delete<void>(`/blocked-time-slots/${id}`),
  checkConflicts: (data: {
    date: string;
    time_slot: string;
    exclude_slot_id?: number;
  }) => api.post<{ conflicts: BlockedTimeSlot[] }>('/blocked-time-slots/check-conflicts', data),
};

// ============================================================================
// Application State API
// ============================================================================

export const stateAPI: StateAPI = {
  get: () => api.get<ApplicationState>('/state'),
  health: () => api.get<HealthCheck>('/health'),
};

// ============================================================================
// Default Export
// ============================================================================

export default api;
