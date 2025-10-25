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
- Automatic weekly cycle reset (Sunday 11:59 PM)

**Tech Stack:**
- Backend: Python Flask + SQLAlchemy (PostgreSQL or JSON fallback)
- Frontend: React SPA (TypeScript migration 15% complete)
- Testing: Playwright (E2E), pytest (backend unit tests)

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

# Backend tests
cd backend
pytest tests/ -v                            # All tests
pytest tests/test_data_handler_parity.py -v # Handler parity check
pytest --cov=utils tests/                   # Coverage report

# TypeScript type checking
cd frontend
npm run type-check
```

### Production Build
```bash
cd frontend
npm run build
```

## Core Architecture

### Data Flow

**1. Data Layer - Hybrid Storage System**
- **PostgreSQL** (production): Tables for roommates, chores, sub_chores, assignments, shopping_items, requests, laundry_slots, blocked_time_slots, application_state
- **JSON Files** (dev/fallback): `backend/data/*.json` - automatically used when DATABASE_URL not configured
- **Critical**: Data lost on container restart in cloud if using JSON mode

**2. Business Logic** (`backend/utils/`)
- `DatabaseDataHandler`: Hybrid handler supporting both PostgreSQL and JSON
- `DataHandler`: Legacy JSON-only handler (compatibility)
- `ChoreAssignmentLogic`: Core fairness algorithms (rotation + weighted random)
- `SchedulerService`: APScheduler for automatic Sunday 11:59 PM cycle reset
- `AuthService`, `SessionManager`: Google OAuth + session management
- `UserCalendarService`: Personal calendar sync
- `SecurityMiddleware`: CSRF, rate limiting, request validation

**3. API Layer** (`backend/app.py`)
- RESTful endpoints with comprehensive error handling
- See API Endpoints section below

**4. Frontend** (`frontend/src/`)
- `services/api.js`: Centralized axios API client
- `contexts/AuthContext.js`: Auth state management
- `components/`: ChoreManager, ShoppingListManager, RequestManager, LaundryScheduler, etc.

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

### Database Configuration

**Production Setup (Neon PostgreSQL):**
```bash
# 1. Get connection string from neon.tech
# 2. Configure .env
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# 3. Migrate data
cd backend
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

### System
- `GET /api/health` - Health check (includes database status)
- `GET /api/scheduler/status` - Automatic reset scheduler status

### Security Notes
- CSRF protection on mutations (requires `X-CSRF-Token` header)
- Rate limiting on auth endpoints
- Login required decorators enforce authentication

## Deployment (Render)

### Pre-Deployment
1. Setup Google OAuth with correct redirect URIs
2. Configure environment variables (see Database Configuration section)
3. Build frontend: `cd frontend && npm run build`

### Key Deployment Notes
- Flask serves React build from `../frontend/build`
- Port auto-detected via `PORT` env var (don't set manually)
- CORS configured for `https://roomie-roster.onrender.com`
- OAuth redirects dynamically generated via `RENDER_SERVICE_NAME`

### Post-Deployment
1. Verify `/api/health` returns database status
2. Test OAuth login flow
3. Check scheduler status: `/api/scheduler/status`

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

## File Structure (Key Locations)

```
backend/
├── app.py                          # Flask application entry point
├── utils/
│   ├── database_data_handler.py    # Hybrid PostgreSQL/JSON handler
│   ├── assignment_logic.py         # Core fairness algorithms
│   ├── scheduler_service.py        # Automatic cycle reset
│   └── security_middleware.py      # CSRF, rate limiting
├── tests/
│   ├── test_data_handler_parity.py # Handler completeness check
│   └── test_decorators.py          # Security decorator tests
└── data/                            # JSON files (fallback mode)

frontend/
├── src/
│   ├── services/api.js             # Centralized API client
│   ├── contexts/AuthContext.js     # Auth state
│   ├── types/                      # TypeScript definitions
│   └── components/                 # React components
└── package.json                    # Note: proxy setting

tests/playwright/
└── e2e/                            # End-to-end test suites
```

## Additional Documentation

- `README.md` - User-facing project documentation
- `API_SETUP_GUIDE.md` - Google OAuth setup instructions
- `DATABASE_SETUP_GUIDE.md` - PostgreSQL migration details
- `AUTHENTICATION_SECURITY.md` - Security implementation details
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - Deployment guide
- `frontend/TYPESCRIPT_MIGRATION.md` - TypeScript migration guide
- `backend/docs/DATA_HANDLER_PARITY.md` - Handler completeness report
