# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

RoomieRoster is a full-stack household chore management application that fairly distributes chores among roommates using intelligent assignment algorithms. The system combines predefined rotation assignments with weighted random distribution based on accumulated points.

**Key Features:**
- **Chore Management**: Create and assign household chores with sub-task tracking
- **Shopping List**: Collaborative shopping with price tracking and purchase history
- **Smart Assignment**: Fair distribution using rotation and weighted algorithms
- **Real-time Updates**: Live collaboration with polling-based synchronization
- **Google Authentication**: Secure OAuth 2.0 login with roommate account linking
- **Personal Calendar Sync**: Sync assigned chores to individual Google Calendars
- **Security**: CSRF protection, rate limiting, and comprehensive security middleware

## Quick Start Commands

### Launch the Application (Recommended)
```bash
python3 launch_app.py
```
This automated launcher handles all setup, dependency installation, and starts both servers concurrently.

### Manual Development Commands

**Backend Setup:**
```bash
cd backend
pip install -r requirements.txt
python app.py
```

**Frontend Setup:**
```bash
cd frontend
npm install
npm start
```

**Testing:**
```bash
cd tests/playwright
npm install && npx playwright install
npm test                    # Run all E2E tests
npm run test:headed         # Run tests with browser visible
npm run test:debug         # Debug mode
npm run test:report        # View test report
```

## Core Architecture

### Data Flow & State Management

The application follows a clear data flow pattern:

1. **Data Layer (`backend/data/`)**: JSON files serve as the persistence layer
   - `chores.json`: Chore definitions with frequency, type, points, and sub-tasks
   - `roommates.json`: Roommate info with current cycle points
   - `state.json`: Application state including assignment history, rotation tracking, and sub-chore completions
   - `shopping_list.json`: Shopping list items with purchase history and status tracking

2. **Business Logic (`backend/utils/`)**: 
   - `DataHandler`: Manages all JSON file operations and data integrity
   - `ChoreAssignmentLogic`: Implements the core fairness algorithms

3. **API Layer (`backend/app.py`)**: RESTful endpoints with comprehensive error handling

4. **Frontend (`frontend/src/`)**: React SPA with component-based architecture
   - `services/api.js`: Centralized API communication with axios and real-time polling
   - `components/`: Feature-specific React components
     - `ChoreManager.js`: Chore CRUD with sub-task management
     - `ShoppingListManager.js`: Shopping list with real-time updates and purchase tracking
     - `SubChoreManager.js`: Sub-task creation and management
     - `SubChoreProgress.js`: Visual progress tracking with checkboxes
   - Proxy configuration routes API calls to backend during development

### Assignment Algorithm Architecture

The core value proposition lies in the sophisticated assignment logic:

**Predefined Chores (Round-Robin):**
- Uses `predefined_chore_states` in `state.json` to track last assignment
- Implements fair rotation: each roommate takes turns in sequential order
- State persists between application runs

**Random Chores (Weighted Distribution):**
- Uses inverse point weighting: roommates with fewer points have higher selection probability
- Points accumulate during cycles based on chore difficulty
- Automatic cycle reset ensures long-term fairness

**Cycle Management:**
- Weekly cycle detection based on `last_run_date`
- Point reset occurs at cycle boundaries
- Prevents gaming of the system through temporal tracking

### Frontend-Backend Integration

The React frontend communicates with Flask via a well-defined API contract:

- **Proxy Setup**: `package.json` proxy routes `/api/*` to `http://localhost:5000`
- **Error Handling**: Axios interceptors provide consistent error handling
- **State Synchronization**: Components refresh data after mutations
- **Real-time Updates**: Polling-based synchronization for shopping list collaboration
  - 5-second polling intervals check for file modification timestamps
  - Visual notifications when other users make changes
  - User-controllable polling with pause/resume functionality

## Key Development Patterns

### Error Handling Strategy
Both backend and frontend implement comprehensive error handling:
- Backend: HTTP status codes with detailed JSON error responses
- Frontend: User-friendly error messages with fallback states
- Launcher: Enhanced subprocess monitoring with real-time error capture

### Data Validation
- Backend: Input validation on all endpoints with specific error messages
- Frontend: Form validation before API calls
- Type safety: Consistent data structure validation throughout

### Testing Philosophy
E2E tests cover complete user workflows rather than isolated units:
- `roommate-management.spec.js`: Full CRUD operations
- `chore-management.spec.js`: Chore lifecycle and form validation  
- `assignment-workflow.spec.js`: End-to-end assignment generation and display

Tests include setup/teardown for data consistency and handle async operations properly.

## Development Notes

### Port Configuration
- Backend: Flask runs on port 5000
- Frontend: React dev server on port 3000
- The launcher includes port conflict detection for 5000

### Data Persistence
JSON files are the single source of truth. When modifying data structures:
1. Update the corresponding `DataHandler` methods
2. Consider migration for existing data files
3. Test both fresh install and upgrade scenarios

### Assignment Logic Modifications
When modifying fairness algorithms:
1. Test with the existing sample data in `backend/data/`
2. Verify both short-term fairness (within cycle) and long-term fairness (across cycles)
3. Consider edge cases: single roommate, no chores, etc.

### Real-time Updates Implementation
The shopping list uses polling-based real-time updates:
- **Metadata Endpoint**: `/api/shopping-list/metadata` provides file modification timestamps
- **Polling Interval**: 5-second checks for changes when polling is enabled
- **Update Detection**: Compares `last_modified` timestamps to detect external changes
- **User Experience**: Visual notifications with manual refresh options

### Sub-Chore System Architecture
Sub-chores extend the core chore system:
- **Data Structure**: Each chore contains a `sub_chores` array with task definitions
- **Completion Tracking**: `sub_chore_completions` in `state.json` tracks progress per assignment
- **Progress Calculation**: Visual progress bars show completion percentage
- **Assignment Integration**: Sub-chores are automatically created for each chore assignment

### Debugging Tools
- Launcher provides detailed startup diagnostics
- Flask app includes comprehensive logging configuration
- Health check endpoint (`/api/health`) for system verification
- Assignment endpoint returns detailed assignment reasoning

## API Endpoints Reference

**Core Operations:**
- `GET/POST /api/roommates` - Roommate management
- `GET/POST /api/chores` - Chore management  
- `POST /api/assign-chores` - Trigger assignment algorithm
- `GET /api/current-assignments` - Retrieve active assignments
- `POST /api/reset-cycle` - Manual cycle reset

**Sub-Chore Management:**
- `GET/POST /api/chores/{id}/sub-chores` - Sub-task CRUD operations
- `PUT/DELETE /api/chores/{id}/sub-chores/{sub_id}` - Individual sub-task management
- `POST /api/chores/{id}/sub-chores/{sub_id}/toggle` - Toggle sub-task completion
- `GET /api/chores/{id}/progress` - Get completion progress for assignments

**Authentication & Security:**
- `POST /api/auth/google-login` - Initiate Google OAuth login (rate limited)
- `GET /api/auth/callback` - Handle OAuth callback (rate limited)
- `GET /api/auth/profile` - Get current user profile (login required)
- `POST /api/auth/link-roommate` - Link Google account to roommate (login required)
- `POST /api/auth/logout` - Logout user (login required)
- `POST /api/auth/revoke` - Revoke Google access (login required)

**Personal Calendar Integration:**
- `GET /api/user-calendar/config` - Get user calendar configuration (login required)
- `POST /api/user-calendar/config` - Save user calendar configuration (login required, CSRF protected)
- `GET /api/user-calendar/calendars` - Get user's available calendars (login required)
- `POST /api/user-calendar/sync-chores` - Sync chores to personal calendar (login required, rate limited, CSRF protected)
- `GET /api/user-calendar/sync-status` - Get calendar sync status (login required)

**Shopping List:**
- `GET/POST /api/shopping-list` - Shopping list item management (supports status filtering)
- `PUT/DELETE /api/shopping-list/{id}` - Individual item operations
- `POST /api/shopping-list/{id}/purchase` - Mark item as purchased with details
- `GET /api/shopping-list/history` - Purchase history with date filtering
- `GET /api/shopping-list/metadata` - Real-time metadata including last modification time

**System:**
- `GET /api/health` - Health check
- `GET /api/state` - Application state inspection

**Key Implementation Notes:**
- The assignment endpoint implements core fairness algorithms
- Sub-chore endpoints support per-assignment completion tracking
- Shopping list metadata endpoint enables real-time collaboration via polling
- Authentication endpoints use OAuth 2.0 with secure session management
- Personal calendar integration syncs chores to individual Google Calendars
- Security features include CSRF protection, rate limiting, and request validation
- All endpoints include comprehensive error handling and validation