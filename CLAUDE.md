# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This directory contains the **RoomieRoster** household chore management application located in the `roomie-roster/` subdirectory. The application is a production-ready full-stack web application with comprehensive testing and automated deployment tools.

## Quick Start Commands

**One-Click Launch (Always Use This):**
```bash
cd roomie-roster && python3 launch_app.py
```

**Testing:**
```bash
cd roomie-roster/tests/playwright
npm install && npx playwright install
npm test                    # Run all E2E tests
npm run test:headed         # Run with browser visible
npm run test:debug         # Debug mode
npm run test:report        # View test report
```

**Frontend Development (Optional):**
```bash
cd roomie-roster/frontend
npm run build              # Production build
npm test                   # React unit tests (if available)
```

**Manual Development (Only if launcher fails):**
```bash
# Backend (Terminal 1)
cd roomie-roster/backend
pip install -r requirements.txt
python app.py

# Frontend (Terminal 2)  
cd roomie-roster/frontend
npm install
npm start
```

## Application Architecture

RoomieRoster is a sophisticated full-stack application featuring:

**Technology Stack:**
- **Backend**: Python Flask 3.0.0 with Flask-CORS 4.0.0, Flask-Session 0.5.0, Google Auth APIs, JSON file persistence
- **Frontend**: React 18.2.0 SPA with Axios 1.6.0, responsive design, testing-library integration
- **Testing**: Playwright 1.40.0 E2E test suite with cross-browser support
- **Deployment**: Automated cross-platform launcher with dependency management and health checks

**Core Business Logic:**
- **Smart Assignment Algorithms**: Dual-mode chore assignment system
  - Predefined chores use round-robin rotation with state persistence
  - Random chores use weighted distribution based on accumulated points
- **Cycle Management**: Weekly automatic cycles with point reset for long-term fairness
- **Real-time Collaboration**: Polling-based updates for shopping list features
- **Sub-task System**: Hierarchical task management with progress tracking

**Key Features:**
- Roommate and chore management with full CRUD operations
- Google OAuth 2.0 authentication with secure session management
- Personal calendar synchronization for assigned chores
- Collaborative shopping list with purchase tracking and history
- Sub-chore creation and completion tracking with visual progress
- Real-time synchronization via file modification timestamp polling
- CSRF protection, rate limiting, and comprehensive security middleware
- Comprehensive error handling and user feedback

## Critical Development Patterns

**Data Architecture:**
- JSON files in `backend/data/` serve as the single source of truth
- `DataHandler` class manages all file operations and data integrity
- Assignment algorithms in `ChoreAssignmentLogic` implement fairness calculations
- Frontend uses proxy configuration to route `/api/*` to backend during development

**Port Configuration:**
- Backend Flask server: `http://localhost:5000-5002` (dynamic port selection with conflict detection)
- Frontend React dev server: `http://localhost:3000`
- Frontend proxy in package.json: `http://localhost:5001` (automatically updated by launcher)
- Launcher includes intelligent port conflict detection and proxy configuration updates

**Error Handling Standards:**
- Backend returns HTTP status codes with detailed JSON error responses
- Frontend displays user-friendly error messages with fallback states
- Launcher provides enhanced subprocess monitoring with real-time error capture

**Testing Philosophy:**
- E2E tests cover complete user workflows, not isolated units
- Tests include proper setup/teardown for data consistency
- Cross-browser testing: Chrome, Firefox, Safari, Mobile Chrome/Safari

## Key API Endpoints

**Core Operations:**
- `GET/POST /api/roommates` - Roommate management
- `GET/POST /api/chores` - Chore management with sub-task support
- `POST /api/assign-chores` - Trigger assignment algorithm
- `GET /api/current-assignments` - Active assignments

**Advanced Features:**
- `GET/POST /api/chores/{id}/sub-chores` - Sub-task management
- `POST /api/chores/{id}/sub-chores/{sub_id}/toggle` - Progress tracking
- `GET/POST /api/shopping-list` - Shopping list with real-time updates
- `GET /api/shopping-list/metadata` - File modification timestamps for polling
- `POST /api/shopping-list/{id}/purchase` - Purchase tracking

**System:**
- `GET /api/health` - Health check
- `GET /api/state` - Application state inspection

## Development Requirements

**When Making Changes:**
1. Always use the automated launcher for development
2. Test changes with the Playwright E2E test suite
3. Ensure both backend and frontend remain functional
4. Maintain data integrity in JSON files during modifications
5. Follow existing patterns for error handling and user feedback

**For Assignment Algorithm Changes:**
1. Test with existing sample data in `backend/data/`
2. Verify both short-term (within cycle) and long-term (across cycles) fairness
3. Handle edge cases: single roommate, no chores, etc.

**For Frontend Changes:**
- Maintain responsive design principles
- Follow component-based architecture patterns
- Ensure real-time updates continue working for shopping list
- Test across different browsers using Playwright

## Documentation Reference

- **Comprehensive Technical Documentation**: `roomie-roster/CLAUDE.md` (detailed architecture, patterns, debugging)
- **User Documentation**: `roomie-roster/README.md` (setup, usage, API reference)
- **Test Documentation**: Test specs in `roomie-roster/tests/playwright/e2e/`

For detailed architecture, implementation patterns, and API specifications, always refer to the comprehensive documentation in `roomie-roster/CLAUDE.md`.