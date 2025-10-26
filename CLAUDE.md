# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

RoomieRoster is a full-stack household chore management app that fairly distributes chores among roommates using intelligent assignment algorithms (round-robin rotation + weighted random distribution).

**Key Features:**
- Chore & roommate management with sub-task tracking
- Shopping list with categories, real-time sync, and purchase history
- Purchase request approval workflow
- Laundry scheduling (app-only, no calendar sync)
- Google OAuth authentication with calendar integration
- **Zeith Productivity Suite** (4 integrated features):
  - **Pomodoro Timer**: Focus sessions with browser notifications
  - **Todo Manager**: Task tracking with priority system and due dates
  - **Mood Journal**: Daily mood/energy/stress tracking with trends
  - **Analytics Dashboard**: Comprehensive productivity metrics with data visualization
- Automatic weekly cycle reset (Sunday 11:59 PM)

**Tech Stack:**
- Backend: Python Flask + SQLAlchemy (PostgreSQL or JSON fallback) + Flask-Migrate (Alembic)
- Frontend: React SPA with Recharts visualization library (TypeScript migration 15% complete)
- Testing: Playwright (E2E), pytest (backend unit tests)
- Production: Gunicorn WSGI server, Flask-Talisman security headers, structured JSON logging

## Quick Start Commands

### Launch Application
```bash
python3 launch_app.py  # Handles all setup, installs dependencies, starts both servers
```

### Manual Development
```bash
# Backend (port 5000/5001)
cd backend
pip install -r requirements.txt
python app.py

# Frontend (port 3000)
cd frontend
npm install
npm start
```

### Testing
```bash
# E2E tests (requires both servers running)
cd tests/playwright
npm install && npx playwright install
npm test                                    # All tests
npx playwright test e2e/specific.spec.js   # Single file
npx playwright test --project="Mobile Safari"  # Mobile
npx playwright test e2e/analytics-dashboard.spec.js  # Productivity feature tests
npx playwright test e2e/pomodoro-complete.spec.js    # Pomodoro workflow
npx playwright test e2e/todo-complete.spec.js        # Todo workflow
npx playwright test e2e/mood-journal.spec.js         # Mood tracking

# Backend tests
cd backend
pytest tests/ -v                            # All tests
pytest tests/test_data_handler_parity.py -v # Handler parity check (CRITICAL)
pytest tests/test_decorators.py -v          # Security decorator tests
pytest tests/test_productivity_api.py -v    # Productivity endpoints
pytest tests/test_productivity_features.py -v  # Feature integration tests
pytest --cov=utils tests/                   # Coverage report

# TypeScript type checking
cd frontend
npm run type-check
```

### Production Build & Deployment
```bash
# Frontend build with verification
cd frontend
npm run build                    # Optimized production build (no source maps)
npm run verify-build            # Verify build structure and size

# Database migrations
cd backend
python scripts/run_migrations.py           # Run pending migrations
python scripts/check_pending_migrations.py # Check migration status

# Pre-deployment validation
python scripts/pre_deploy_check.py   # Comprehensive deployment readiness check
python scripts/validate_env.py       # Validate environment variables

# Local production testing
gunicorn -w 2 -b 0.0.0.0:5000 app:app  # Test with production server
```

## Core Architecture

### Data Flow

**1. Data Layer - Hybrid Storage System**
- **PostgreSQL** (production): 17 tables organized in 3 groups:
  - **Core RoomieRoster** (9 tables): roommates, chores, sub_chores, assignments, shopping_items, requests, laundry_slots, blocked_time_slots, application_state
  - **Calendar Integration** (4 tables): calendar_configs, calendar_sync_state, calendar_chore_sync_logs, calendar_events
  - **Zeith Productivity** (4 tables): pomodoro_sessions, todo_items, mood_entries, analytics_snapshots
- **JSON Files** (dev/fallback): `backend/data/*.json` - automatically used when DATABASE_URL not configured
- **Critical**: Data lost on container restart in cloud if using JSON mode
- **Migrations**: Flask-Migrate (Alembic) for zero-downtime schema changes

**2. Business Logic** (`backend/utils/`)
- `DatabaseDataHandler`: Hybrid handler supporting both PostgreSQL and JSON
- `DataHandler`: Legacy JSON-only handler (compatibility)
- `ChoreAssignmentLogic`: Core fairness algorithms (rotation + weighted random)
- `SchedulerService`: APScheduler for automatic Sunday 11:59 PM cycle reset
- `AuthService`, `SessionManager`: Google OAuth + session management
- `UserCalendarService`: Personal calendar sync
- `SecurityMiddleware`: CSRF, rate limiting, request validation
- `logger.py`: Structured JSON logging (production) / colored logging (development)

**3. API Layer** (`backend/app.py`)
- RESTful endpoints with comprehensive error handling
- See API Endpoints section below

**4. Frontend** (`frontend/src/`)
- `services/api.js`: Centralized axios API client (40+ API endpoints organized in 10 modules)
- `contexts/AuthContext.js`: Auth state management
- `components/`:
  - **Core Features**: ChoreManager, ShoppingListManager, RequestManager, LaundryScheduler
  - **Zeith Productivity**: PomodoroTimer, TodoManager, MoodJournal, AnalyticsDashboard (uses Recharts)

### Assignment Algorithm (The Core Value Proposition)

**Predefined Chores (Round-Robin):**
- Tracks last assignment in `state.json` → `predefined_chore_states`
- Each roommate takes turns sequentially
- Persists between runs

**Random Chores (Weighted Distribution):**
- Inverse point weighting: fewer points = higher selection probability
- Points accumulate during cycle based on chore difficulty
- Automatic reset at cycle boundaries ensures long-term fairness

**Cycle Management:**
- Weekly auto-reset: Sunday 11:59 PM via APScheduler
- Manual reset available via `/api/reset-cycle`
- Resets all roommate points and clears current assignments

### Zeith Productivity Features (Integrated Suite)

**1. Pomodoro Timer**
- Focus sessions (25 min), short breaks (5 min), long breaks (15 min)
- Browser notifications on completion
- Link sessions to chores or todos
- Real-time sync (2-second polling for active sessions)
- Session history and statistics

**2. Todo Manager**
- Priority system: low/medium/high/urgent
- Status tracking: pending/in_progress/completed
- Category filtering (Work, Personal, etc.)
- Due date management with visual indicators
- Estimated vs actual Pomodoros tracking
- Can be linked to chores

**3. Mood Journal**
- Daily entries with mood/energy/stress levels (1-5 scale)
- Sleep hours tracking (0-24)
- Activity tagging (exercise, meditation, etc.)
- 7-day history view
- Trend analysis by period (week/month/year)

**4. Analytics Dashboard**
- **Recharts visualizations**:
  - Bar chart: Chores completed vs assigned
  - Line chart: Daily Pomodoro sessions
  - Line chart: Mood trends (mood/energy/stress)
- Current cycle metrics (completion rates, pending todos)
- Pomodoro statistics (total sessions, minutes, avg length)
- Period selection (week/month)

**Key Integration Points:**
- All features require authentication + roommate linkage
- Rate limited (50 requests/minute per user)
- CSRF protected mutations
- Data syncs with chore assignments and calendar events

### Database Configuration

**Production Setup (Neon PostgreSQL):**
```bash
# 1. Get connection string from neon.tech
# 2. Configure .env
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# 3. Run migrations (Alembic)
cd backend
python scripts/run_migrations.py              # Apply all pending migrations
python scripts/check_pending_migrations.py    # Verify migration status

# Legacy: Manual data migration from JSON (one-time)
python migrate_data.py
```

**Environment Variables (Production):**
```bash
# Database
DATABASE_URL=postgresql://...

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Security
FLASK_SECRET_KEY=...  # 32-char hex string
ROOMIE_WHITELIST=email1@domain.com,email2@domain.com

# Auto-set by Render
PORT=...  # Don't set manually
RENDER_SERVICE_NAME=...  # For OAuth redirect URI generation
```

**Redirect URIs (Google OAuth):**
- Dev: `http://localhost:5000/api/auth/callback`, `http://localhost:5001/api/auth/callback`
- Prod: `https://your-app.onrender.com/api/auth/callback` (auto-detected via RENDER_SERVICE_NAME)
- Custom domain: Set `APP_BASE_URL` env var

## Key Development Patterns

### Port Configuration
- Backend: 5000 (launcher uses 5001 if conflict)
- Frontend: 3000
- **Frontend proxy in package.json**: `http://localhost:5000` (launcher auto-updates if needed)

### Real-time Updates (Shopping List)
- Polling-based: 5-second intervals
- `/api/shopping-list/metadata` returns `last_modified` timestamp
- Frontend compares timestamps, shows notifications when changed

### Sub-Chore System
- Data: Each chore has `sub_chores` array
- Tracking: `sub_chore_completions` in `state.json` (per-assignment)
- UI: Progress bars show completion percentage

### Shopping List Categories
- Create, rename, delete categories
- Items auto-reassigned when category deleted
- Persistence: Uses SQLAlchemy `flag_modified()` for nested updates

### Request Management
- Auto-approval threshold (default $10)
- Requires roommate approvals above threshold
- Auto-adds to shopping list when approved

### Laundry Scheduling
- **App-only feature** - does NOT sync to Google Calendar
- 2-hour time slots with machine type selection
- Conflict prevention via time slot validation

### Testing Philosophy
- E2E tests cover complete workflows (not isolated units)
- Mobile testing: iPhone, iPad, Samsung Galaxy emulation
- Backend parity checks prevent DatabaseDataHandler incompleteness

### TypeScript Migration (15% complete)
- Types defined in `frontend/src/types/`
- `api.js` → `api.ts` (proof of concept)
- Components pending migration
- Run: `npm run type-check`

## Critical Development Notes

### Database Migration Workflow (Flask-Migrate/Alembic)

**When to create migrations:**
- Adding/removing tables
- Adding/removing columns
- Changing column types or constraints
- Adding/removing indexes or foreign keys

**Creating new migrations:**
```bash
cd backend
flask db migrate -m "Description of changes"  # Auto-generate migration
flask db upgrade                              # Apply migration locally
pytest tests/ -v                              # Test before committing
```

**Production migration flow:**
1. Migrations run automatically on Render deployment via `scripts/run_migrations.py`
2. Health check validates migration status before accepting traffic
3. Zero-downtime deployment: new instance runs migrations, then replaces old instance

**IMPORTANT**: Never delete migration files. Always create new migrations to undo changes.

**Migration troubleshooting:**
```bash
python scripts/check_pending_migrations.py  # Check what's pending
flask db current                            # Show current revision
flask db history                            # Show migration history
flask db downgrade <revision>               # Rollback (use with caution)
```

### Data Handler Parity
**Problem**: DatabaseDataHandler was 68% incomplete, breaking multiple features.
**Solution**: Run parity check after ANY DataHandler/DatabaseDataHandler changes:
```bash
cd backend
pytest tests/test_data_handler_parity.py -v
# OR
python3 scripts/check_handler_parity.py --fail-on-missing
```

### Security Decorator Testing
Known bug regressions prevented:
- `@auth_rate_limited` TypeError when used without parameters
- `@rate_limit` incorrect parameter names
- Decorator stacking order issues

**Always run after middleware changes:**
```bash
pytest tests/test_decorators.py -v
```

### Structured Logging (Production)

**Environment-based logging** (`backend/utils/logger.py`):
- **Development**: Human-readable colored logs
- **Production**: JSON-formatted logs for easy parsing

**Features:**
- Correlation IDs for request tracing
- Automatic sensitive data sanitization (tokens, passwords, emails)
- Request/response timing
- Environment-specific log levels

**Viewing logs:**
```bash
# Render.com dashboard
# Or via CLI:
render logs -s <service-id> --tail

# Local structured logging
export FLASK_ENV=production
python app.py  # Outputs JSON logs
```

### Launcher Script Behavior
- Checks requirements (Python 3.8+, Node 16+)
- Installs missing dependencies
- Handles port conflicts (tries 5000, falls back to 5001)
- Auto-updates frontend proxy in package.json if needed
- Graceful shutdown on Ctrl+C

### Frontend Proxy Gotcha
If running servers manually and backend is on 5001:
```bash
# Option 1: Update package.json
"proxy": "http://localhost:5001"

# Option 2: Use launcher (handles this automatically)
python3 launch_app.py
```

## API Endpoints (Essential)

### Core Operations
- `GET/POST /api/roommates` - Manage roommates
- `GET/POST /api/chores` - Manage chores
- `POST /api/assign-chores` - Run assignment algorithm
- `GET /api/current-assignments` - Get assignments
- `POST /api/reset-cycle` - Manual cycle reset

### Sub-Chores
- `GET/POST /api/chores/{id}/sub-chores` - CRUD
- `POST /api/chores/{id}/sub-chores/{sub_id}/toggle` - Toggle completion

### Authentication (Rate Limited)
- `POST /api/auth/google-login` - Start OAuth
- `GET /api/auth/callback` - OAuth callback
- `GET /api/auth/profile` - User profile (login required)
- `POST /api/auth/link-roommate` - Link account (login required)
- `POST /api/auth/logout` - Logout

### Shopping List
- `GET/POST /api/shopping-list` - CRUD (supports status filtering)
- `PUT/DELETE /api/shopping-list/{id}` - Update/delete
- `POST /api/shopping-list/{id}/purchase` - Mark purchased
- `GET /api/shopping-list/metadata` - Real-time metadata
- `GET/POST /api/shopping-list/categories` - Category management

### Requests
- `GET/POST /api/requests` - CRUD
- `POST /api/requests/{id}/approve` - Approve/decline
- `GET /api/requests/pending` - Pending requests

### Calendar Integration (Login Required)
- `GET/POST /api/user-calendar/config` - User calendar config
- `POST /api/user-calendar/sync-chores` - Sync to personal calendar (CSRF protected, rate limited)

### Laundry (App-Only, No Calendar Sync)
- `GET/POST /api/laundry-slots` - CRUD
- `GET /api/laundry-slots/availability` - Check availability

### Zeith Productivity (Login + Roommate Link Required, Rate Limited: 50/min)

**Pomodoro (6 endpoints):**
- `POST /api/pomodoro/start` - Start focus/break session
- `POST /api/pomodoro/complete` - Complete active session
- `POST /api/pomodoro/:id/pause` - Pause session
- `GET /api/pomodoro/active` - Get active session
- `GET /api/pomodoro/history` - Get history (filter by status, date)
- `GET /api/pomodoro/stats` - Get statistics (by period)

**Todo Items (6 endpoints):**
- `GET /api/todos` - Get all todos (filter by status, category, priority)
- `POST /api/todos` - Create todo
- `GET /api/todos/:id` - Get specific todo
- `PUT /api/todos/:id` - Update todo
- `DELETE /api/todos/:id` - Delete todo
- `POST /api/todos/:id/complete` - Mark completed

**Mood Journal (5 endpoints):**
- `GET /api/mood/entries` - Get entries (filter by date range)
- `POST /api/mood/entries` - Create entry
- `GET /api/mood/entries/:id` - Get specific entry
- `PUT /api/mood/entries/:id` - Update entry
- `GET /api/mood/trends` - Get aggregated trends (by period)

**Analytics (3 endpoints):**
- `GET /api/analytics/snapshots` - Get daily snapshots
- `POST /api/analytics/snapshot` - Create snapshot
- `GET /api/analytics/dashboard` - Get comprehensive dashboard data

**Note:** See `backend/docs/PRODUCTIVITY_API.md` for complete documentation

### System
- `GET /api/health` - Health check (includes database, migrations, scheduler, productivity features)
- `GET /api/scheduler/status` - Automatic reset scheduler status

### Security Notes
- CSRF protection on mutations (requires `X-CSRF-Token` header)
- Rate limiting: Auth (5/5min), API (100/min), Calendar (20/min), Productivity (50/min)
- Login required decorators enforce authentication
- Productivity features require roommate linkage

## Deployment (Render)

### Pre-Deployment
1. Run pre-deployment checks:
   ```bash
   cd backend
   python scripts/pre_deploy_check.py  # Comprehensive validation
   python scripts/validate_env.py      # Environment variable check
   ```
2. Setup Google OAuth with correct redirect URIs
3. Configure environment variables (use `.env.production.template` as reference)
4. Build frontend: `cd frontend && npm run build && npm run verify-build`
5. Review `docs/RENDER_DEPLOYMENT_GUIDE.md` for complete checklist

### Key Deployment Notes
- **Automated Deployment Flow** (defined in `render.yaml`):
  1. Build frontend (optimized, no source maps)
  2. Install backend dependencies
  3. Run database migrations automatically (`scripts/run_migrations.py`)
  4. Start gunicorn with 2 workers
  5. Health check validates before routing traffic
- Flask serves React build from `../frontend/build`
- Port auto-detected via `PORT` env var (don't set manually)
- CORS configured for `https://roomie-roster.onrender.com`
- OAuth redirects dynamically generated via `RENDER_SERVICE_NAME`
- **Security Headers**: Flask-Talisman enforces HTTPS, HSTS, CSP (production only)
- **Logging**: Structured JSON logs in production for easy parsing

### Post-Deployment
1. Verify `/api/health` returns 200 with all features healthy
2. Test OAuth login flow
3. Check scheduler status: `/api/scheduler/status`
4. Test all 4 Zeith productivity features
5. Monitor logs for errors (first 24 hours)
6. Verify data persistence after redeploy (zero-downtime deployment)

## Common Issues

**Backend won't start:**
- Check port 5000 not occupied: `lsof -ti:5000 | xargs kill -9`
- Verify Python 3.8+: `python3 --version`

**Frontend can't connect:**
- Verify backend running on expected port
- Check `proxy` in `frontend/package.json` matches backend port
- Clear browser cache for CORS issues

**Data not persisting (production):**
- Verify DATABASE_URL configured (JSON mode loses data on restart)
- Check `/api/health` endpoint for database status

**OAuth errors:**
- Verify redirect URIs in Google Console match app URLs
- Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET set
- Ensure `OAUTHLIB_RELAX_TOKEN_SCOPE=1` in environment

**Parity test failures:**
- Run: `pytest tests/test_data_handler_parity.py -v`
- Implement missing methods in DatabaseDataHandler
- Check `backend/docs/DATA_HANDLER_PARITY.md` for report

**Zeith productivity features not working:**
- Verify user is logged in with Google OAuth
- Ensure user is linked to a roommate profile (`/api/auth/link-roommate`)
- Check rate limit not exceeded (50 requests/minute for productivity)
- Verify DATABASE_URL set (productivity features require PostgreSQL, not JSON mode)
- Check `/api/health` endpoint shows all productivity features as healthy
- Review browser console for 403 (not linked) or 429 (rate limited) errors

**Migration errors:**
- Run: `python scripts/check_pending_migrations.py`
- Verify DATABASE_URL is correct and database is accessible
- Check migration files haven't been manually edited
- Review logs for specific SQL errors
- If stuck: Check Alembic revision table: `SELECT * FROM alembic_version;`

## File Structure (Key Locations)

```
backend/
├── app.py                          # Flask application entry point (80+ endpoints)
├── migrations/                     # Flask-Migrate (Alembic) migrations
│   ├── alembic.ini                # Alembic configuration
│   ├── env.py                     # Migration environment
│   └── versions/                  # Migration scripts (versioned)
├── scripts/                       # Deployment & utility scripts
│   ├── run_migrations.py          # Production migration runner
│   ├── check_pending_migrations.py # Migration status validator
│   ├── pre_deploy_check.py        # Comprehensive deployment validator
│   └── validate_env.py            # Environment variable validator
├── utils/
│   ├── database_data_handler.py   # Hybrid PostgreSQL/JSON handler
│   ├── assignment_logic.py        # Core fairness algorithms
│   ├── scheduler_service.py       # Automatic cycle reset
│   ├── security_middleware.py     # CSRF, rate limiting
│   └── logger.py                  # Structured JSON logging
├── tests/
│   ├── test_data_handler_parity.py      # Handler completeness check (CRITICAL)
│   ├── test_decorators.py               # Security decorator tests
│   ├── test_productivity_api.py         # Productivity endpoint tests
│   └── test_productivity_features.py    # Feature integration tests
├── docs/
│   └── PRODUCTIVITY_API.md        # Complete API documentation (20 endpoints)
└── data/                           # JSON files (fallback mode)

frontend/
├── src/
│   ├── services/api.js            # Centralized API client (40+ endpoints)
│   ├── contexts/AuthContext.js    # Auth state
│   ├── types/                     # TypeScript definitions
│   └── components/                # React components
│       ├── ChoreManager.js        # Core chore management
│       ├── ShoppingListManager.js # Shopping list
│       ├── PomodoroTimer.js       # Zeith: Focus timer
│       ├── TodoManager.js         # Zeith: Task tracking
│       ├── MoodJournal.js         # Zeith: Mood tracking
│       └── AnalyticsDashboard.js  # Zeith: Data visualization
├── scripts/
│   └── verify-build.js            # Build verification tool
└── package.json                   # Note: proxy setting

tests/playwright/
├── e2e/                           # End-to-end test suites
│   ├── analytics-dashboard.spec.js  # Productivity feature tests
│   ├── pomodoro-complete.spec.js    # Pomodoro workflow
│   ├── todo-complete.spec.js        # Todo workflow
│   └── mood-journal.spec.js         # Mood tracking
└── playwright.config.js           # Cross-browser config

docs/
├── RENDER_DEPLOYMENT_GUIDE.md     # 500+ line deployment guide
└── (other documentation...)

Configuration Files:
├── render.yaml                    # Render.com deployment configuration
├── .env.production.template       # Production environment template
└── launch_app.py                  # One-click launcher script
```

## Additional Documentation

**Core Documentation:**
- `README.md` - User-facing project documentation
- `API_SETUP_GUIDE.md` - Google OAuth setup instructions
- `DATABASE_SETUP_GUIDE.md` - PostgreSQL migration details
- `AUTHENTICATION_SECURITY.md` - Security implementation details

**Deployment & Production:**
- `docs/RENDER_DEPLOYMENT_GUIDE.md` - **Comprehensive 500+ line deployment guide** (PRIMARY REFERENCE)
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - Deployment checklist
- `.env.production.template` - Production environment template with all variables
- `render.yaml` - Infrastructure-as-Code for Render.com

**Zeith Productivity:**
- `backend/docs/PRODUCTIVITY_API.md` - **Complete API documentation for 20 productivity endpoints**
- `ZEITH_PHASE1_COMPLETE.md` - Backend API implementation report
- `ZEITH_PHASE2_COMPLETE.md` - Database integration report
- `ZEITH_PHASE3_COMPLETE.md` - Frontend development report

**Development & Testing:**
- `frontend/TYPESCRIPT_MIGRATION.md` - TypeScript migration guide (15% complete)
- `backend/docs/DATA_HANDLER_PARITY.md` - Handler completeness report

**Phase Reports:**
- `PHASE4_TEST_REPORT.md` - Testing infrastructure report
- `PHASE5_DEPLOYMENT_COMPLETE.md` - **Production readiness report** (zero-downtime deployment)
