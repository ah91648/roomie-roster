import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Include cookies for CSRF tokens
});

// CSRF token management
let csrfToken = null;

const getCSRFToken = async () => {
  if (!csrfToken) {
    try {
      const response = await api.get('/auth/profile');
      if (response.data && response.data.user && response.data.user.csrf_token) {
        csrfToken = response.data.user.csrf_token;
      }
    } catch (error) {
      // CSRF token not available (user not logged in)
      console.log('CSRF token not available');
    }
  }
  return csrfToken;
};

// Request interceptor for logging and CSRF token
api.interceptors.request.use(
  async (config) => {
    console.log(`Making ${config.method.toUpperCase()} request to ${config.url}`);
    
    // Add CSRF token for non-GET requests
    if (config.method !== 'get') {
      const token = await getCSRFToken();
      if (token) {
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

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
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

// Export function to clear tokens (for logout)
export const clearTokens = () => {
  csrfToken = null;
};

// Export function to force CSRF token refresh (for auth state changes)
export const refreshCSRFToken = async () => {
  csrfToken = null;
  return await getCSRFToken();
};

// Chores API
export const choreAPI = {
  getAll: () => api.get('/chores'),
  create: (chore) => api.post('/chores', chore),
  update: (id, chore) => api.put(`/chores/${id}`, chore),
  delete: (id) => api.delete(`/chores/${id}`),
};

// Sub-chores API
export const subChoreAPI = {
  getAll: (choreId, config = {}) => api.get(`/chores/${choreId}/sub-chores`, config),
  create: (choreId, subChore) => api.post(`/chores/${choreId}/sub-chores`, subChore),
  update: (choreId, subChoreId, subChore) => api.put(`/chores/${choreId}/sub-chores/${subChoreId}`, subChore),
  delete: (choreId, subChoreId) => api.delete(`/chores/${choreId}/sub-chores/${subChoreId}`),
  toggle: (choreId, subChoreId, assignmentIndex = null) => 
    api.post(`/chores/${choreId}/sub-chores/${subChoreId}/toggle`, { assignment_index: assignmentIndex }),
  getProgress: (choreId, assignmentIndex = null) => 
    api.get(`/chores/${choreId}/progress${assignmentIndex !== null ? `?assignment_index=${assignmentIndex}` : ''}`),
};

// Shopping list API
export const shoppingListAPI = {
  getAll: (status = null) => api.get(`/shopping-list${status ? `?status=${status}` : ''}`),
  create: (item) => api.post('/shopping-list', item),
  update: (id, item) => api.put(`/shopping-list/${id}`, item),
  delete: (id) => api.delete(`/shopping-list/${id}`),
  markPurchased: (id, purchaseData) => api.post(`/shopping-list/${id}/purchase`, purchaseData),
  getHistory: (days = 30) => api.get(`/shopping-list/history?days=${days}`),
  getMetadata: () => api.get('/shopping-list/metadata'),
  clearAllHistory: () => api.post('/shopping-list/clear-all-history'),
  clearHistoryFromDate: (fromDate) => api.post('/shopping-list/clear-history-from-date', { from_date: fromDate }),
  // Category management
  getCategories: () => api.get('/shopping-list/categories'),
  createCategory: (categoryName) => api.post('/shopping-list/categories', { category_name: categoryName }),
  renameCategory: (oldName, newName) => api.put(`/shopping-list/categories/${encodeURIComponent(oldName)}`, { new_name: newName }),
  deleteCategory: (categoryName) => api.delete(`/shopping-list/categories/${encodeURIComponent(categoryName)}`),
  getByCategory: (status = null) => api.get(`/shopping-list/by-category${status ? `?status=${status}` : ''}`),
};

// Request API
export const requestAPI = {
  getAll: (status = null) => api.get(`/requests${status ? `?status=${status}` : ''}`),
  create: (request) => api.post('/requests', request),
  update: (id, request) => api.put(`/requests/${id}`, request),
  delete: (id) => api.delete(`/requests/${id}`),
  approve: (id, approvalData) => api.post(`/requests/${id}/approve`, approvalData),
  getPendingForUser: (userId) => api.get(`/requests/pending/${userId}`),
  getMetadata: () => api.get('/requests/metadata'),
};

// Roommates API
export const roommateAPI = {
  getAll: () => api.get('/roommates'),
  create: (roommate) => api.post('/roommates', roommate),
  update: (id, roommate) => api.put(`/roommates/${id}`, roommate),
  delete: (id) => api.delete(`/roommates/${id}`),
};

// Assignments API
export const assignmentAPI = {
  assignChores: () => api.post('/assign-chores'),
  getCurrent: () => api.get('/current-assignments'),
  resetCycle: () => api.post('/reset-cycle'),
};

// Laundry scheduling API
export const laundryAPI = {
  getAll: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.date) queryParams.append('date', params.date);
    if (params.roommate_id) queryParams.append('roommate_id', params.roommate_id);
    if (params.status) queryParams.append('status', params.status);
    
    const queryString = queryParams.toString();
    return api.get(`/laundry-slots${queryString ? `?${queryString}` : ''}`);
  },
  create: (slot) => api.post('/laundry-slots', slot),
  update: (id, slot) => api.put(`/laundry-slots/${id}`, slot),
  delete: (id) => api.delete(`/laundry-slots/${id}`),
  complete: (id, completionData = {}) => api.post(`/laundry-slots/${id}/complete`, completionData),
  checkConflicts: (conflictData) => api.post('/laundry-slots/check-conflicts', conflictData),
  getMetadata: () => api.get('/laundry-slots/metadata'),
};

// Calendar integration API
export const calendarAPI = {
  getStatus: () => api.get('/calendar/status'),
  setupCredentials: (credentials) => api.post('/calendar/setup-credentials', { credentials }),
  getOAuthUrl: () => api.get('/calendar/oauth-url'),
  getCalendarList: () => api.get('/calendar/calendars'),
  getConfig: () => api.get('/calendar/config'),
  saveConfig: (config) => api.post('/calendar/config', config),
  createEvent: (eventData) => api.post('/calendar/create-event', eventData),
  deleteEvent: (calendarId, eventId) => api.delete('/calendar/delete-event', { data: { calendar_id: calendarId, event_id: eventId } }),
};

// Authentication API
export const authAPI = {
  getStatus: () => api.get('/auth/status'),
  initiateGoogleLogin: (redirectUri) => api.post('/auth/google-login', { redirect_uri: redirectUri }),
  getProfile: () => api.get('/auth/profile'),
  refreshSession: () => api.post('/auth/refresh'),
  verifyRoommateLink: () => api.get('/auth/verify-roommate-link'),
  linkRoommate: (roommateId) => api.post('/auth/link-roommate', { roommate_id: roommateId }),
  unlinkRoommate: () => api.post('/auth/unlink-roommate'),
  logout: () => api.post('/auth/logout'),
  revokeAccess: () => api.post('/auth/revoke'),
  setupCredentials: (credentials) => api.post('/auth/setup-credentials', { credentials }),
};

// User Calendar API
export const userCalendarAPI = {
  getConfig: () => api.get('/user-calendar/config'),
  saveConfig: (config) => api.post('/user-calendar/config', config),
  getCalendars: () => api.get('/user-calendar/calendars'),
  syncChores: () => api.post('/user-calendar/sync-chores'),
  getSyncStatus: () => api.get('/user-calendar/sync-status'),
};

// Blocked Time Slots API
export const blockedTimeSlotsAPI = {
  getAll: (params = {}) => api.get('/blocked-time-slots', { params }),
  create: (data) => api.post('/blocked-time-slots', data),
  update: (id, data) => api.put(`/blocked-time-slots/${id}`, data),
  delete: (id) => api.delete(`/blocked-time-slots/${id}`),
  checkConflicts: (data) => api.post('/blocked-time-slots/check-conflicts', data),
};

// Application state API
export const stateAPI = {
  get: () => api.get('/state'),
  health: () => api.get('/health'),
};

// Pomodoro API (6 endpoints)
export const pomodoroAPI = {
  // Start a new Pomodoro session
  start: (sessionData) => api.post('/pomodoro/start', sessionData),

  // Complete an active session
  complete: (sessionId, notes = null) => api.post('/pomodoro/complete', {
    session_id: sessionId,
    notes
  }),

  // Pause an in-progress session
  pause: (sessionId, notes = null) => api.post(`/pomodoro/${sessionId}/pause`, { notes }),

  // Get current active session
  getActive: () => api.get('/pomodoro/active'),

  // Get session history with optional filters
  getHistory: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.status) queryParams.append('status', params.status);
    if (params.session_type) queryParams.append('session_type', params.session_type);
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    if (params.limit) queryParams.append('limit', params.limit);

    const queryString = queryParams.toString();
    return api.get(`/pomodoro/history${queryString ? `?${queryString}` : ''}`);
  },

  // Get Pomodoro statistics
  getStats: (period = 'week') => api.get(`/pomodoro/stats?period=${period}`),
};

// Todo API (6 endpoints)
export const todoAPI = {
  // Get all todos with optional filters
  getAll: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.status) queryParams.append('status', params.status);
    if (params.category) queryParams.append('category', params.category);
    if (params.priority) queryParams.append('priority', params.priority);

    const queryString = queryParams.toString();
    return api.get(`/todos${queryString ? `?${queryString}` : ''}`);
  },

  // Create a new todo
  create: (todoData) => api.post('/todos', todoData),

  // Get a specific todo by ID
  getOne: (id) => api.get(`/todos/${id}`),

  // Update a todo
  update: (id, todoData) => api.put(`/todos/${id}`, todoData),

  // Delete a todo
  delete: (id) => api.delete(`/todos/${id}`),

  // Mark todo as completed
  complete: (id, notes = null) => api.post(`/todos/${id}/complete`, { notes }),
};

// Mood API (5 endpoints)
export const moodAPI = {
  // Get mood entries with optional date range
  getEntries: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    if (params.limit) queryParams.append('limit', params.limit);

    const queryString = queryParams.toString();
    return api.get(`/mood/entries${queryString ? `?${queryString}` : ''}`);
  },

  // Create a new mood entry
  create: (moodData) => api.post('/mood/entries', moodData),

  // Get a specific mood entry by ID
  getOne: (id) => api.get(`/mood/entries/${id}`),

  // Update a mood entry
  update: (id, moodData) => api.put(`/mood/entries/${id}`, moodData),

  // Get mood trends
  getTrends: (period = 'week') => api.get(`/mood/trends?period=${period}`),
};

// Analytics API (3 endpoints)
export const analyticsAPI = {
  // Get analytics snapshots
  getSnapshots: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    if (params.limit) queryParams.append('limit', params.limit);

    const queryString = queryParams.toString();
    return api.get(`/analytics/snapshots${queryString ? `?${queryString}` : ''}`);
  },

  // Create a daily analytics snapshot
  createSnapshot: () => api.post('/analytics/snapshot'),

  // Get comprehensive analytics dashboard
  getDashboard: (period = 'week') => api.get(`/analytics/dashboard?period=${period}`),
};

export default api;