# Zeith Productivity API Documentation

**Version:** 2.0
**Last Updated:** 2025-10-25

This document details the 20 REST API endpoints for Zeith productivity features: Pomodoro sessions, Todo items, Mood tracking, and Analytics.

---

## Table of Contents

- [Authentication & Security](#authentication--security)
- [Pomodoro Endpoints (6)](#pomodoro-endpoints)
- [Todo Endpoints (6)](#todo-endpoints)
- [Mood Endpoints (5)](#mood-endpoints)
- [Analytics Endpoints (3)](#analytics-endpoints)
- [Error Codes](#error-codes)

---

## Authentication & Security

### Requirements

All productivity endpoints require:
- **Authentication**: User must be logged in (`@login_required`)
- **Roommate Link**: User must be linked to a roommate profile
- **Rate Limiting**: 50 requests per minute per user (`productivity` category)
- **CSRF Protection**: All mutations (POST/PUT/DELETE) require CSRF token

### Rate Limits

| Category       | Limit            |
|----------------|------------------|
| Productivity   | 50/minute        |
| Auth           | 5/5 minutes      |
| API (general)  | 100/minute       |
| Calendar       | 20/minute        |

### Common Headers

```http
Authorization: Bearer <token>
X-CSRF-Token: <csrf_token>
Content-Type: application/json
```

### Common Error Responses

**403 Forbidden** - Not linked to roommate:
```json
{
  "error": "You must be linked to a roommate to use productivity features"
}
```

**429 Too Many Requests** - Rate limit exceeded:
```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```

---

## Pomodoro Endpoints

### 1. Start Pomodoro Session

Start a new focus session, short break, or long break.

**Endpoint:** `POST /api/pomodoro/start`

**Request Body:**
```json
{
  "session_type": "focus",           // "focus", "short_break", or "long_break"
  "planned_duration_minutes": 25,    // Optional, defaults based on type
  "chore_id": 5,                     // Optional: link to chore
  "todo_id": 12,                     // Optional: link to todo
  "notes": "Working on feature X"    // Optional
}
```

**Duration Defaults:**
- `focus`: 25 minutes
- `short_break`: 5 minutes
- `long_break`: 15 minutes

**Success Response (201):**
```json
{
  "id": 42,
  "roommate_id": 1,
  "start_time": "2025-10-25T14:30:00Z",
  "planned_duration_minutes": 25,
  "session_type": "focus",
  "chore_id": 5,
  "todo_id": 12,
  "notes": "Working on feature X",
  "status": "in_progress"
}
```

**Error Responses:**
- **400**: Invalid session_type / Active session already exists
- **403**: Not linked to roommate

---

### 2. Complete Pomodoro Session

Mark an active Pomodoro session as completed.

**Endpoint:** `POST /api/pomodoro/complete`

**Request Body:**
```json
{
  "session_id": 42,
  "notes": "Completed successfully"  // Optional
}
```

**Success Response (200):**
```json
{
  "id": 42,
  "status": "completed",
  "end_time": "2025-10-25T14:55:00Z",
  "actual_duration_minutes": 25,
  "notes": "Completed successfully"
}
```

**Error Responses:**
- **400**: session_id required / Session already completed
- **404**: Session not found or access denied

---

### 3. Pause Pomodoro Session

Pause an in-progress Pomodoro session.

**Endpoint:** `POST /api/pomodoro/:id/pause`

**Request Body:**
```json
{
  "notes": "Taking a break"  // Optional
}
```

**Success Response (200):**
```json
{
  "id": 42,
  "status": "paused",
  "notes": "Taking a break"
}
```

**Error Responses:**
- **400**: Cannot pause session with status 'completed'
- **404**: Session not found or access denied

---

### 4. Get Active Pomodoro

Get the current user's active Pomodoro session.

**Endpoint:** `GET /api/pomodoro/active`

**Success Response (200):**
```json
{
  "id": 42,
  "session_type": "focus",
  "start_time": "2025-10-25T14:30:00Z",
  "planned_duration_minutes": 25,
  "status": "in_progress"
}
```

**No Active Session (200):**
```json
null
```

---

### 5. Get Pomodoro History

Get past Pomodoro sessions with optional filtering.

**Endpoint:** `GET /api/pomodoro/history`

**Query Parameters:**
- `status` (optional): `completed`, `in_progress`, or `paused`
- `start_date` (optional): ISO8601 format (e.g., `2025-10-20T00:00:00Z`)
- `limit` (optional): Maximum number of results

**Example Request:**
```
GET /api/pomodoro/history?status=completed&limit=10
```

**Success Response (200):**
```json
[
  {
    "id": 41,
    "session_type": "focus",
    "start_time": "2025-10-25T13:00:00Z",
    "end_time": "2025-10-25T13:25:00Z",
    "actual_duration_minutes": 25,
    "status": "completed"
  },
  ...
]
```

---

### 6. Get Pomodoro Statistics

Get aggregated Pomodoro statistics for a time period.

**Endpoint:** `GET /api/pomodoro/stats`

**Query Parameters:**
- `period` (optional): `day`, `week`, `month`, or `year` (default: `week`)

**Success Response (200):**
```json
{
  "total_sessions": 45,
  "completed_sessions": 42,
  "total_minutes": 1050,
  "avg_session_length": 25,
  "completion_rate": 93.3,
  "period_start": "2025-10-18T00:00:00Z",
  "period_end": "2025-10-25T00:00:00Z"
}
```

---

## Todo Endpoints

### 1. Get Todos

Get all todo items for the current user with optional filtering.

**Endpoint:** `GET /api/todos`

**Query Parameters:**
- `status` (optional): `pending`, `in_progress`, or `completed`
- `category` (optional): Filter by category (e.g., `Work`, `Personal`)

**Success Response (200):**
```json
[
  {
    "id": 15,
    "roommate_id": 1,
    "title": "Complete project proposal",
    "description": "Draft and finalize Q1 proposal",
    "category": "Work",
    "priority": "high",
    "status": "in_progress",
    "due_date": "2025-10-30T17:00:00Z",
    "estimated_pomodoros": 3,
    "actual_pomodoros": 1,
    "created_at": "2025-10-20T10:00:00Z"
  },
  ...
]
```

---

### 2. Create Todo

Create a new todo item.

**Endpoint:** `POST /api/todos`

**Request Body:**
```json
{
  "title": "Complete project proposal",        // Required
  "description": "Draft and finalize",         // Optional
  "category": "Work",                          // Optional, default: "Personal"
  "priority": "high",                          // Optional: low/medium/high/urgent, default: medium
  "due_date": "2025-10-30T17:00:00Z",         // Optional, must be future
  "chore_id": 5,                               // Optional: link to chore
  "estimated_pomodoros": 3,                    // Optional, default: 1
  "tags": ["proposal", "urgent"],              // Optional
  "display_order": 0                           // Optional, default: 0
}
```

**Success Response (201):**
```json
{
  "id": 16,
  "roommate_id": 1,
  "title": "Complete project proposal",
  "status": "pending",
  "created_at": "2025-10-25T15:00:00Z",
  ...
}
```

**Error Responses:**
- **400**: Title required / Invalid priority / Due date must be in future

---

### 3. Get Specific Todo

Get details of a specific todo item.

**Endpoint:** `GET /api/todos/:id`

**Success Response (200):**
```json
{
  "id": 15,
  "title": "Complete project proposal",
  "status": "in_progress",
  ...
}
```

**Error Response:**
- **404**: Todo not found or access denied

---

### 4. Update Todo

Update an existing todo item.

**Endpoint:** `PUT /api/todos/:id`

**Request Body (partial update):**
```json
{
  "title": "Updated title",
  "priority": "urgent",
  "status": "in_progress"
}
```

**Success Response (200):**
```json
{
  "id": 15,
  "title": "Updated title",
  "priority": "urgent",
  "status": "in_progress",
  ...
}
```

**Error Responses:**
- **400**: Title cannot be empty / Invalid priority/status
- **404**: Todo not found or access denied

---

### 5. Delete Todo

Delete a todo item.

**Endpoint:** `DELETE /api/todos/:id`

**Success Response (200):**
```json
{
  "message": "Todo deleted successfully"
}
```

**Error Response:**
- **404**: Todo not found or access denied

---

### 6. Complete Todo

Mark a todo as completed.

**Endpoint:** `POST /api/todos/:id/complete`

**Request Body (optional):**
```json
{
  "actual_pomodoros": 4
}
```

**Success Response (200):**
```json
{
  "id": 15,
  "status": "completed",
  "completed_at": "2025-10-25T15:30:00Z",
  "actual_pomodoros": 4
}
```

**Error Responses:**
- **400**: Todo is already completed
- **404**: Todo not found or access denied

---

## Mood Endpoints

### 1. Get Mood Entries

Get mood journal entries for the current user.

**Endpoint:** `GET /api/mood/entries`

**Query Parameters:**
- `start_date` (optional): ISO8601 format
- `end_date` (optional): ISO8601 format

**Success Response (200):**
```json
[
  {
    "id": 8,
    "roommate_id": 1,
    "mood_level": 4,
    "energy_level": 3,
    "stress_level": 2,
    "sleep_hours": 7.5,
    "activities": ["exercise", "meditation"],
    "notes": "Feeling productive",
    "entry_date": "2025-10-25T09:00:00Z",
    "created_at": "2025-10-25T09:15:00Z"
  },
  ...
]
```

---

### 2. Create Mood Entry

Create a new mood journal entry.

**Endpoint:** `POST /api/mood/entries`

**Request Body:**
```json
{
  "mood_level": 4,                      // Required: 1-5 (1=very_sad, 5=great)
  "energy_level": 3,                    // Optional: 1-5 (1=exhausted, 5=energized)
  "stress_level": 2,                    // Optional: 1-5 (1=relaxed, 5=overwhelmed)
  "sleep_hours": 7.5,                   // Optional: 0-24
  "activities": ["exercise", "work"],   // Optional: array of strings
  "notes": "Feeling good today",        // Optional
  "entry_date": "2025-10-25T09:00:00Z"  // Optional, defaults to now
}
```

**Success Response (201):**
```json
{
  "id": 9,
  "mood_level": 4,
  "energy_level": 3,
  "created_at": "2025-10-25T15:00:00Z",
  ...
}
```

**Error Responses:**
- **400**: mood_level is required / Levels must be between 1-5 / sleep_hours must be 0-24

---

### 3. Get Specific Mood Entry

Get a specific mood entry.

**Endpoint:** `GET /api/mood/entries/:id`

**Success Response (200):**
```json
{
  "id": 8,
  "mood_level": 4,
  ...
}
```

**Error Response:**
- **404**: Mood entry not found or access denied

---

### 4. Update Mood Entry

Update an existing mood entry.

**Endpoint:** `PUT /api/mood/entries/:id`

**Request Body (partial update):**
```json
{
  "mood_level": 5,
  "notes": "Updated notes"
}
```

**Success Response (200):**
```json
{
  "id": 8,
  "mood_level": 5,
  "notes": "Updated notes",
  "updated_at": "2025-10-25T16:00:00Z",
  ...
}
```

**Error Responses:**
- **400**: Validation errors
- **404**: Entry not found or access denied

---

### 5. Get Mood Trends

Get aggregated mood trend analytics.

**Endpoint:** `GET /api/mood/trends`

**Query Parameters:**
- `period` (optional): `week`, `month`, or `year` (default: `month`)

**Success Response (200):**
```json
{
  "avg_mood": 4.2,
  "avg_energy": 3.8,
  "avg_stress": 2.1,
  "mood_variance": 0.8,
  "entry_count": 28,
  "period_start": "2025-09-25T00:00:00Z",
  "period_end": "2025-10-25T00:00:00Z"
}
```

---

## Analytics Endpoints

### 1. Get Analytics Snapshots

Get daily analytics snapshots for historical tracking.

**Endpoint:** `GET /api/analytics/snapshots`

**Query Parameters:**
- `start_date` (optional): ISO8601 date format
- `end_date` (optional): ISO8601 date format

**Success Response (200):**
```json
[
  {
    "id": 12,
    "roommate_id": 1,
    "snapshot_date": "2025-10-25",
    "chores_completed": 3,
    "chores_assigned": 5,
    "total_points_earned": 45,
    "pomodoros_completed": 8,
    "todos_completed": 4,
    "avg_mood_score": 4.2,
    "productivity_score": 85.5
  },
  ...
]
```

---

### 2. Create Analytics Snapshot

Create a new daily analytics snapshot.

**Endpoint:** `POST /api/analytics/snapshot`

**Request Body (all optional with defaults):**
```json
{
  "snapshot_date": "2025-10-25",     // Default: today
  "chores_completed": 3,             // Default: 0
  "chores_assigned": 5,              // Default: 0
  "total_points_earned": 45,         // Default: 0
  "pomodoros_completed": 8,          // Default: 0
  "todos_completed": 4,              // Default: 0
  "avg_mood_score": 4.2,             // Optional
  "productivity_score": 85.5         // Optional
}
```

**Success Response (201):**
```json
{
  "id": 13,
  "roommate_id": 1,
  "snapshot_date": "2025-10-25",
  ...
}
```

**Error Response:**
- **400**: Field type validation errors

---

### 3. Get Analytics Dashboard

Get comprehensive analytics dashboard with aggregated data.

**Endpoint:** `GET /api/analytics/dashboard`

**Query Parameters:**
- `period` (optional): `week` or `month` (default: `week`)

**Success Response (200):**
```json
{
  "period": "week",
  "current_cycle": {
    "chores_assigned": 8,
    "chores_completed": 6,
    "completion_rate": 75.0,
    "pending_todos": 5,
    "completed_todos": 12
  },
  "pomodoro": {
    "total_sessions": 35,
    "completed_sessions": 33,
    "total_minutes": 825,
    "avg_session_length": 25,
    "completion_rate": 94.3
  },
  "mood": {
    "avg_mood": 4.1,
    "avg_energy": 3.7,
    "avg_stress": 2.3,
    "entry_count": 7
  },
  "snapshots": [...],
  "insights": {
    "most_productive_day": null,
    "avg_daily_pomodoros": 5.0,
    "mood_productivity_correlation": null
  }
}
```

---

## Error Codes

| Code | Meaning               | Example                                      |
|------|-----------------------|----------------------------------------------|
| 200  | Success               | Resource retrieved successfully              |
| 201  | Created               | Resource created successfully                |
| 400  | Bad Request           | Invalid input / Validation error             |
| 403  | Forbidden             | Not linked to roommate / Permission denied   |
| 404  | Not Found             | Resource not found or access denied          |
| 429  | Too Many Requests     | Rate limit exceeded                          |
| 500  | Internal Server Error | Unexpected server error                      |

---

## Integration Examples

### Example: Complete Pomodoro Workflow

```javascript
// 1. Start focus session
const startResponse = await fetch('/api/pomodoro/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken
  },
  body: JSON.stringify({
    session_type: 'focus',
    planned_duration_minutes: 25,
    todo_id: 15,
    notes: 'Working on proposal'
  })
});

const session = await startResponse.json();
console.log('Session started:', session.id);

// 2. After 25 minutes...
const completeResponse = await fetch('/api/pomodoro/complete', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken
  },
  body: JSON.stringify({
    session_id: session.id,
    notes: 'Completed successfully!'
  })
});

// 3. Update linked todo
await fetch(`/api/todos/${15}`, {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken
  },
  body: JSON.stringify({
    actual_pomodoros: 1,
    status: 'in_progress'
  })
});
```

---

**For questions or issues, refer to the main CLAUDE.md documentation or backend/README.md**
