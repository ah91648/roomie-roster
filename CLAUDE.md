# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

RoomieRoster is a full-stack household chore management application that fairly distributes chores among roommates using intelligent assignment algorithms. The system combines predefined rotation assignments with weighted random distribution based on accumulated points.

**Key Features:**
- **Chore Management**: Create and assign household chores with sub-task tracking
- **Shopping List**: Collaborative shopping with price tracking and purchase history
- **Request Management**: Roommate approval system for purchasing requests with auto-approval thresholds
- **Laundry Scheduling**: Time slot management for shared laundry facilities with load tracking
- **Blocked Time Slots**: Calendar integration for blocked time periods that prevent scheduling conflicts
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
npx playwright test mobile-navigation.spec.js  # Test mobile navigation specifically
npx playwright test --project="Mobile Safari"  # Test specific mobile browser
```

**Production Build:**
```bash
cd frontend
npm run build               # Build frontend for production
```

**Development Server Commands:**
```bash
# Frontend development server (from frontend/)
npm start                   # Starts React dev server on port 3000
npm test                    # Run React component tests

# Backend development server (from backend/)
python app.py               # Starts Flask server on port 5000/5001
```

**Linting and Code Quality:**
```bash
# Frontend (uses built-in react-scripts)
cd frontend
npm run build               # Includes linting as part of build process

# Backend (Python code follows PEP 8)
cd backend
python -m flake8 .          # If flake8 is installed for linting
```

## Database Configuration

RoomieRoster supports both **PostgreSQL** (recommended for production) and **JSON files** (development/fallback) for data persistence.

### Quick Database Setup

**For Production (Neon PostgreSQL - Recommended):**

1. **Sign up for Neon PostgreSQL** (Free 3GB tier):
   - Visit [neon.tech](https://neon.tech) and create an account
   - Create a new project and database
   - Copy the connection string from your dashboard

2. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your database URL:
   DATABASE_URL=postgresql://username:password@ep-xxx-pooler.us-east-2.aws.neon.tech/dbname?sslmode=require
   ```

3. **Run Data Migration:**
   ```bash
   cd backend
   python migrate_data.py  # Migrates existing JSON data to PostgreSQL
   ```

**For Development (JSON Files):**
- No setup required - application automatically uses JSON files if no database is configured
- Data stored in `backend/data/` directory

### Environment Variables

**Required for Production:**
```bash
# Database (choose one option)
DATABASE_URL=postgresql://...  # Option 1: Full connection string
# OR
DATABASE_HOST=your-host        # Option 2: Individual parameters
DATABASE_NAME=your-db
DATABASE_USER=your-username
DATABASE_PASSWORD=your-password

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# Security
FLASK_SECRET_KEY=your_32_char_hex_key
ROOMIE_WHITELIST=email1@domain.com,email2@domain.com
```

### Storage Architecture

The application automatically detects and uses the best available storage:

1. **PostgreSQL Mode** (when DATABASE_URL is configured):
   - Persistent storage that survives container restarts
   - Relational data integrity with foreign keys
   - Better performance and scalability
   - Automatic table creation and migration support

2. **JSON File Mode** (fallback when no database configured):
   - Simple file-based storage in `backend/data/`
   - Works for development but **data is lost on container restart** in cloud deployments
   - Automatically used when database connection fails

### Database Migration

**Migrating from JSON to PostgreSQL:**

```bash
cd backend

# 1. Set up your database URL in .env
echo "DATABASE_URL=your_neon_connection_string" >> .env

# 2. Run the migration script
python migrate_data.py

# 3. Verify migration success
python -c "
from utils.database_init import database_initializer
from flask import Flask
app = Flask(__name__)
with app.app_context():
    status = database_initializer.get_database_status()
    print('Database Status:', status)
"
```

**Migration Features:**
- Preserves all existing data and relationships
- Handles data type conversions and date parsing
- Provides detailed migration logs and error handling
- Supports rollback to JSON files if needed
- Validates data integrity post-migration

### Database Management Commands

```bash
# Check database status
curl http://localhost:5000/api/health

# Reset database (WARNING: Deletes all data!)
python -c "
from utils.database_init import database_initializer
from flask import Flask
app = Flask(__name__)
database_initializer.reset_database(app)
"

# Manual migration from specific data directory
python migrate_data.py --data-dir /path/to/data
```

## Core Architecture

### Data Flow & State Management

The application follows a clear data flow pattern:

1. **Data Layer**: Hybrid PostgreSQL/JSON persistence system
   - **PostgreSQL (Production)**: Relational database with proper foreign keys and data integrity
     - Tables: `roommates`, `chores`, `sub_chores`, `assignments`, `shopping_items`, `requests`, `laundry_slots`, `blocked_time_slots`, `application_state`
   - **JSON Files (Development/Fallback)**: File-based storage in `backend/data/`
     - `chores.json`: Chore definitions with frequency, type, points, and sub-tasks
     - `roommates.json`: Roommate info with current cycle points
     - `state.json`: Application state including assignment history, rotation tracking, and sub-chore completions
     - `shopping_list.json`: Shopping list items with purchase history and status tracking
     - `requests.json`: Purchase requests with approval workflows and auto-approval rules
     - `laundry_slots.json`: Laundry scheduling with time slots, load types, and machine reservations
     - `blocked_time_slots.json`: Blocked time periods for preventing scheduling conflicts

2. **Business Logic (`backend/utils/`)**: 
   - `DatabaseDataHandler`: Hybrid data management supporting both PostgreSQL and JSON files
   - `DataHandler`: Legacy JSON file operations (maintained for compatibility)
   - `DatabaseConfig`: Database connection and configuration management
   - `DatabaseModels`: SQLAlchemy models mirroring JSON data structures
   - `DatabaseInit`: Database initialization, table creation, and health checks
   - `ChoreAssignmentLogic`: Implements the core fairness algorithms
   - `SchedulerService`: Handles automatic weekly cycle resets using APScheduler
   - `AuthService`: Handles Google OAuth authentication and session management
   - `CalendarService`: Google Calendar API integration for chore sync
   - `SecurityMiddleware`: CSRF protection, rate limiting, and request validation
   - `SessionManager`: User session and authentication state management
   - `UserCalendarService`: Personal calendar configuration and sync functionality

3. **API Layer (`backend/app.py`)**: RESTful endpoints with comprehensive error handling

4. **Frontend (`frontend/src/`)**: React SPA with component-based architecture
   - `services/api.js`: Centralized API communication with axios and real-time polling
   - `contexts/AuthContext.js`: React context for authentication state management
   - `components/`: Feature-specific React components
     - `ChoreManager.js`: Chore CRUD with sub-task management
     - `ShoppingListManager.js`: Shopping list with real-time updates and purchase tracking
     - `RequestManager.js`: Purchase request approval workflow with threshold management
     - `LaundryScheduler.js`: Time slot booking for shared laundry facilities
     - `BlockedTimeSlotsManager.js`: Management of blocked time periods to prevent scheduling conflicts
     - `SubChoreManager.js`: Sub-task creation and management
     - `SubChoreProgress.js`: Visual progress tracking with checkboxes
     - `AssignmentDisplay.js`: Shows current chore assignments organized by roommate
     - `RoommateManager.js`: Roommate CRUD operations with validation
     - `GoogleLoginButton.js`: OAuth login interface component
     - `UserProfile.js`: User account management and linked roommate display
     - `CalendarSettings.js`: Google Calendar integration configuration
     - `UserCalendarSettings.js`: Personal calendar sync preferences
   - Proxy configuration routes API calls to backend during development (currently set to port 5001)

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

### Responsive Design Architecture
The application uses a mobile-first responsive design approach:
- **Desktop Navigation**: Horizontal tabs with icons and text labels side-by-side
- **Mobile Navigation**: Vertical tab layout with icons above text labels for better touch interaction
- **CSS Media Queries**: Breakpoint at 768px switches between desktop and mobile layouts
- **Mobile Optimization**: Smaller fonts (0.75rem labels, 1.2rem icons), reduced padding, centered alignment
- **Cross-browser Compatibility**: Tested across Safari, Chrome, Firefox on both desktop and mobile

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
- `authentication-flow.spec.js`: OAuth login and session management
- `calendar-integration.spec.js`: Google Calendar sync functionality
- `laundry-scheduling.spec.js`: Time slot booking and conflict detection
- `mobile-navigation.spec.js`: Mobile Safari navigation and responsive design validation
- `deployment-verification.spec.js`: Production deployment validation

Tests include setup/teardown for data consistency and handle async operations properly.

### Test Infrastructure Features
- **Visual Testing**: Screenshots captured for debugging and verification in `tests/playwright/screenshots/`
- **Cross-browser Testing**: Chrome, Firefox, Safari compatibility across desktop and mobile
- **Mobile Testing**: Comprehensive responsive design validation with device emulation (iPhone, iPad, Samsung Galaxy)
- **Mobile Navigation Testing**: Specific tests for mobile Safari tab visibility and functionality
- **Authentication Testing**: OAuth flow verification with mock users
- **Deployment Testing**: Live site validation and feature verification
- **Performance Testing**: Load times and responsiveness metrics
- **Device-Specific Testing**: Individual mobile device configurations with proper user agent strings

## Development Notes

### Port Configuration
- Backend: Flask runs on port 5000 (launcher script may use 5001 if 5000 is occupied)
- Frontend: React dev server on port 3000
- **Important**: Frontend proxy in `package.json` currently points to port 5001 - update if needed for consistency
- The launcher includes port conflict detection and automatic port selection
- **Production**: Render automatically assigns port via `PORT` environment variable - do not set manually

### Single Test Execution
When debugging specific test scenarios:
```bash
cd tests/playwright
npx playwright test roommate-management.spec.js    # Run single test file
npx playwright test --grep "add roommate"          # Run tests matching pattern
npx playwright test --debug roommate-management    # Debug specific test file
npx playwright test mobile-navigation.spec.js --headed  # Test mobile navigation with visible browser
npx playwright test --project="chromium"           # Run tests on specific browser
npx playwright test --project="Mobile Chrome"      # Test specific mobile configuration
```

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

### Request Management System
Purchase requests require roommate approval before being added to shopping list:
- **Auto-Approval**: Items under configurable threshold (default $10) are automatically approved
- **Approval Workflow**: Items above threshold require minimum number of roommate approvals
- **Status Tracking**: Tracks approved, declined, and pending requests with approval history
- **Shopping List Integration**: Approved requests are automatically added to shopping list

### Laundry Scheduling System
Manages shared laundry facility access with time slot reservations:
- **Time Slot Management**: 2-hour booking windows with machine type selection
- **Load Type Tracking**: Categorizes laundry by type (lights, darks, delicates, etc.)
- **Capacity Planning**: Tracks estimated vs actual loads for better scheduling
- **Status Management**: Handles scheduled, in-progress, and completed laundry sessions
- **Conflict Prevention**: Prevents double-booking of time slots and machines

### Blocked Time Slots System
Manages time periods that are unavailable for laundry scheduling:
- **Time Blocking**: Mark specific time slots as unavailable with custom reasons
- **Calendar Integration**: Optionally sync blocked slots to all users' Google Calendars
- **Conflict Detection**: Prevents scheduling laundry during blocked periods
- **Flexible Management**: Add, edit, delete blocked slots with date-specific filtering
- **Automatic Validation**: Checks for conflicts when creating or updating time blocks

### Automatic Cycle Reset System
The application now includes automated weekly cycle resets to ensure consistent fairness:
- **Scheduled Reset**: Automatic cycle reset every Sunday at 11:59 PM using APScheduler
- **Background Processing**: Uses BackgroundScheduler to run independently of user requests
- **Graceful Handling**: Includes misfire grace period and error handling for reliability
- **Manual Override**: Maintains existing manual reset functionality through API endpoint
- **Logging**: Comprehensive logging of automatic and manual reset operations
- **Status Monitoring**: API endpoint to check scheduler status and next scheduled reset

**Key Implementation Details:**
- APScheduler v3.10.4 with BackgroundScheduler for Flask compatibility
- Cron trigger configured for Sunday 23:59 weekly execution
- Automatic cleanup of current assignments and reset of roommate cycle points
- Event listeners for job execution monitoring and error handling
- Graceful shutdown handling with atexit registration

### Debugging Tools
- Launcher provides detailed startup diagnostics with real-time error capture
- Flask app includes comprehensive logging configuration with stdout/stderr handlers
- Health check endpoint (`/api/health`) for system verification
- Assignment endpoint returns detailed assignment reasoning
- Enhanced error handlers with full stack traces
- Development CORS configuration for local testing
- Mobile testing suite with device-specific screenshots and browser console logging
- Playwright test reports with visual debugging information

### Deployment Architecture
The application is designed for Render deployment with these key considerations:
- **Static Serving**: Flask serves React build files from `../frontend/build`
- **Environment Variables**: Critical for Google OAuth, Flask security, and roommate whitelist
- **CORS Configuration**: Production-ready with specific origin whitelisting
- **Port Binding**: Automatically detects Render's assigned port via environment
- **Error Handling**: Comprehensive logging for production debugging
- **Security Features**: CSRF protection, rate limiting, session management

### Required Environment Variables
For production deployment, these environment variables must be configured:
- `GOOGLE_CLIENT_ID`: OAuth client ID from Google Cloud Console
- `GOOGLE_CLIENT_SECRET`: OAuth client secret from Google Cloud Console  
- `FLASK_SECRET_KEY`: Random 32-character hex string for session security
- `ROOMIE_WHITELIST`: Comma-separated list of allowed email addresses
- `PORT`: Automatically set by Render (do not configure manually)

**Optional Environment Variables:**
- `RENDER_SERVICE_NAME`: Automatically set by Render, used for dynamic redirect URI generation
- `APP_BASE_URL`: Custom base URL override for OAuth redirects (useful for custom domains)

### Google API Setup
Before deployment, Google APIs must be configured (see `API_SETUP_GUIDE.md` for detailed instructions):

**Required Google APIs:**
- Google OAuth 2.0 / Identity API (essential for authentication)
- Google Calendar API (optional, for calendar integration)

**OAuth Configuration Steps:**
1. Create Google Cloud project and enable APIs
2. Configure OAuth consent screen with appropriate scopes
3. Create OAuth 2.0 credentials with proper redirect URIs
4. Add test users during development phase
5. Update redirect URIs after deployment
6. Publish app for production use

**Critical Redirect URIs:**
The application now dynamically determines redirect URIs based on environment:
- Development: `http://localhost:5000/api/auth/callback`, `http://localhost:5001/api/auth/callback`
- Production: `https://your-app.onrender.com/api/auth/callback` (automatically detected via `RENDER_SERVICE_NAME`)
- Custom domains: Set `APP_BASE_URL` environment variable for custom redirect URI generation

**Dynamic Redirect URI Features:**
- Automatically detects Render deployment environment
- Handles port conflicts in development (5000 vs 5001)
- Validates redirect URIs for security
- Supports custom base URLs via environment variables

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

**Request Management:**
- `GET/POST /api/requests` - Purchase request management with approval workflows
- `PUT/DELETE /api/requests/{id}` - Individual request operations
- `POST /api/requests/{id}/approve` - Approve or decline purchase requests
- `GET /api/requests/pending` - Get requests awaiting approval
- `GET /api/requests/history` - Purchase request history and decisions

**Laundry Scheduling:**
- `GET/POST /api/laundry-slots` - Laundry time slot management
- `PUT/DELETE /api/laundry-slots/{id}` - Individual slot operations
- `GET /api/laundry-slots/availability` - Check available time slots
- `POST /api/laundry-slots/{id}/complete` - Mark laundry session as completed
- `GET /api/laundry-slots/schedule` - Get upcoming laundry schedule

**Blocked Time Slots:**
- `GET/POST /api/blocked-time-slots` - Blocked time slot management (supports date filtering)
- `PUT/DELETE /api/blocked-time-slots/{id}` - Individual blocked slot operations
- `POST /api/blocked-time-slots/check-conflicts` - Check for scheduling conflicts

**System:**
- `GET /api/health` - Health check
- `GET /api/state` - Application state inspection
- `GET /api/scheduler/status` - Get automatic scheduler status and next reset time

**Key Implementation Notes:**
- The assignment endpoint implements core fairness algorithms
- Sub-chore endpoints support per-assignment completion tracking
- Shopping list metadata endpoint enables real-time collaboration via polling
- Request management implements approval workflows with configurable thresholds
- Laundry scheduling prevents conflicts through time slot validation
- Blocked time slots integrate with calendar sync and conflict detection
- Authentication endpoints use OAuth 2.0 with secure session management
- Personal calendar integration syncs chores to individual Google Calendars
- Automatic cycle reset runs every Sunday at 11:59 PM via APScheduler
- Manual reset endpoint preserves existing functionality alongside automatic resets
- Scheduler status endpoint provides monitoring of automatic reset jobs
- Security features include CSRF protection, rate limiting, and request validation
- All endpoints include comprehensive error handling and validation

## Dependencies and Installation

### Backend Dependencies (requirements.txt)
```
Flask==3.0.0
Flask-CORS==4.0.0
Flask-Session==0.5.0
python-dateutil==2.8.2
google-auth==2.23.4
google-auth-oauthlib==1.1.0
google-api-python-client==2.108.0
requests==2.31.0
gunicorn==21.2.0
apscheduler==3.10.4
```

### Frontend Dependencies (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "axios": "^1.6.0",
    "@testing-library/jest-dom": "^6.0.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/user-event": "^14.0.0"
  }
}
```

### Test Dependencies (tests/playwright/package.json)
```json
{
  "devDependencies": {
    "@playwright/test": "^1.40.0"
  }
}
```