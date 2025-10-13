# TypeScript Migration Guide

**Status**: 🟡 In Progress (Phase 1 Complete)
**Start Date**: 2025-10-12
**Target Completion**: Incremental (phased approach)

## Overview

This document tracks the incremental migration of RoomieRoster frontend from JavaScript to TypeScript. The migration follows a phased approach to minimize disruption while adding compile-time type safety and improved developer experience.

## Benefits of TypeScript

- **Type Safety**: Catch errors at compile-time instead of runtime
- **Better IDE Support**: Autocomplete, IntelliSense, and inline documentation
- **Refactoring Confidence**: Rename and restructure code with confidence
- **Self-Documenting**: Types serve as inline documentation
- **Fewer Bugs**: Many common JavaScript errors are caught before deployment

## Migration Strategy

### Phase 1: Infrastructure Setup ✅ COMPLETE

- [x] Create `tsconfig.json` with gradual strictness settings
- [x] Add TypeScript dependencies to `package.json`
- [x] Create comprehensive type definitions (`src/types/`)
  - [x] `models.ts` - All data model types
  - [x] `api.ts` - API endpoint types
  - [x] `index.ts` - Central export file
- [x] Convert `api.js` to `api.ts` as proof of concept
- [x] Add `type-check` script to `package.json`

### Phase 2: Service Layer Migration 🔄 TODO

**Priority**: High
**Estimated Effort**: 2-3 hours

Services to convert:
- [ ] Keep `api.ts` (already done)
- [ ] Any other service files in `src/services/`

### Phase 3: Context Migration 🔄 TODO

**Priority**: High
**Estimated Effort**: 3-4 hours

Contexts to convert:
- [ ] `AuthContext.js` → `AuthContext.tsx`
  - Add User type
  - Type all context values and methods
  - Type all provider props

### Phase 4: Utility Functions 🔄 TODO

**Priority**: Medium
**Estimated Effort**: 1-2 hours

- [ ] Convert any utility functions in `src/utils/`
- [ ] Add proper types for all utility functions
- [ ] Export types alongside utilities

### Phase 5: Component Migration (Gradual) 🔄 TODO

**Priority**: Medium
**Estimated Effort**: 10-15 hours (spread over time)

**Strategy**: Convert components from simplest to most complex

#### Group A: Simple Presentational Components (Start Here)
- [ ] Simple display components with minimal props
- [ ] Components without complex state management
- [ ] Components that use the already-typed API

#### Group B: Manager Components
- [ ] `RoommateManager.js` → `RoommateManager.tsx`
- [ ] `ChoreManager.js` → `ChoreManager.tsx`
- [ ] `ShoppingListManager.js` → `ShoppingListManager.tsx`
- [ ] `RequestManager.js` → `RequestManager.tsx`
- [ ] `LaundryScheduler.js` → `LaundryScheduler.tsx`
- [ ] `SubChoreManager.js` → `SubChoreManager.tsx`
- [ ] `BlockedTimeSlotsManager.js` → `BlockedTimeSlotsManager.tsx`

#### Group C: Complex Components
- [ ] `AssignmentDisplay.js` → `AssignmentDisplay.tsx`
- [ ] `SubChoreProgress.js` → `SubChoreProgress.tsx`
- [ ] `UserProfile.js` → `UserProfile.tsx`
- [ ] `CalendarSettings.js` → `CalendarSettings.tsx`
- [ ] `UserCalendarSettings.js` → `UserCalendarSettings.tsx`
- [ ] `GoogleLoginButton.js` → `GoogleLoginButton.tsx`

#### Group D: Main App Component
- [ ] `App.js` → `App.tsx` (last component to convert)

### Phase 6: Strictness Increase 🔄 TODO

**Priority**: Low
**Estimated Effort**: Ongoing

Once most files are converted, gradually enable stricter TypeScript settings:

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true
  }
}
```

## Current TypeScript Configuration

The `tsconfig.json` is configured for **gradual migration**:

- ✅ `allowJs: true` - JavaScript files can coexist with TypeScript
- ✅ `checkJs: false` - Don't type-check existing JavaScript files
- ✅ `strict: false` - Start with loose type checking
- ✅ `noImplicitAny: false` - Allow implicit `any` types
- ✅ Path aliases configured for cleaner imports:
  ```typescript
  import { Chore } from '@/types';
  import { choreAPI } from '@services/api';
  ```

## Type Definitions Reference

### Available Types

All types are exported from `src/types/index.ts`:

```typescript
import {
  // Data Models
  Roommate,
  Chore,
  Assignment,
  ShoppingItem,
  Request,
  LaundrySlot,
  BlockedTimeSlot,
  User,
  CalendarConfig,

  // API Types
  ChoreAPI,
  RoommateAPI,
  ShoppingListAPI,
  RequestAPI,
  AssignmentAPI,

  // Utility Types
  ApiResponse,
  ApiError,
  LoadingState,
  NotificationState
} from '@/types';
```

### Type Categories

1. **Model Types** (`models.ts`):
   - Core data structures (Roommate, Chore, Assignment, etc.)
   - Create/Update interfaces for each model
   - Enum types for status fields

2. **API Types** (`api.ts`):
   - API endpoint interfaces
   - Request/Response types
   - Query parameter types

3. **UI State Types**:
   - Loading states
   - Form data types
   - Notification types

## Migration Checklist for Components

When converting a component from `.js` to `.tsx`, follow this checklist:

### 1. Rename File
```bash
git mv ComponentName.js ComponentName.tsx
```

### 2. Add Type Imports
```typescript
import type { Roommate, RoommateCreate } from '@/types';
```

### 3. Type Props
```typescript
interface Props {
  roommates: Roommate[];
  onAdd: (roommate: RoommateCreate) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

const Component: React.FC<Props> = ({ roommates, onAdd, onDelete }) => {
  // ...
};
```

### 4. Type State
```typescript
const [roommates, setRoommates] = useState<Roommate[]>([]);
const [loading, setLoading] = useState<boolean>(false);
const [error, setError] = useState<string | null>(null);
```

### 5. Type Event Handlers
```typescript
const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  // ...
};

const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  const { name, value } = e.target;
  // ...
};
```

### 6. Type API Calls
```typescript
// API is already typed in api.ts, so responses are automatically typed
const fetchRoommates = async () => {
  try {
    const response = await roommateAPI.getAll();
    // response.data is automatically typed as Roommate[]
    setRoommates(response.data);
  } catch (error) {
    console.error(error);
  }
};
```

### 7. Run Type Check
```bash
npm run type-check
```

## Common Migration Patterns

### Pattern 1: Typing useState
```typescript
// Before (JavaScript)
const [data, setData] = useState(null);

// After (TypeScript)
const [data, setData] = useState<Chore | null>(null);
```

### Pattern 2: Typing Props with Children
```typescript
interface Props {
  title: string;
  children: React.ReactNode;
}

const Component: React.FC<Props> = ({ title, children }) => (
  <div>
    <h1>{title}</h1>
    {children}
  </div>
);
```

### Pattern 3: Typing Form Data
```typescript
// Use predefined form types
import { ChoreFormData } from '@/types';

const [formData, setFormData] = useState<ChoreFormData>({
  name: '',
  frequency: 'weekly',
  type: 'random',
  points: 0
});
```

### Pattern 4: Typing API Responses
```typescript
// API calls are automatically typed via api.ts
const loadChores = async () => {
  try {
    const response = await choreAPI.getAll();
    // response.data is Chore[]
    setChores(response.data);
  } catch (error) {
    console.error(error);
  }
};
```

### Pattern 5: Optional Props
```typescript
interface Props {
  title: string;
  subtitle?: string; // Optional
  onClose?: () => void; // Optional callback
}
```

## Testing TypeScript Code

### Run Type Checking
```bash
# Check types without emitting files
npm run type-check

# Watch mode for continuous type checking
npx tsc --noEmit --watch
```

### Run Tests
```bash
# React tests work the same with TypeScript
npm test
```

### Build Application
```bash
# TypeScript is compiled as part of the build
npm run build
```

## Common TypeScript Errors and Solutions

### Error: "Cannot find module '@/types'"
**Solution**: Make sure `tsconfig.json` has the correct path mappings:
```json
{
  "compilerOptions": {
    "baseUrl": "src",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### Error: "Property X does not exist on type Y"
**Solution**: Check if the type definition is complete. Add missing properties to type definitions in `src/types/models.ts`.

### Error: "Type 'null' is not assignable to type 'X'"
**Solution**: Use union types or optional properties:
```typescript
// Option 1: Union type
const [data, setData] = useState<Chore | null>(null);

// Option 2: Optional property
interface Props {
  data?: Chore;
}
```

### Error: "Object is possibly 'undefined'"
**Solution**: Use optional chaining and nullish coalescing:
```typescript
// Before
const name = user.linkedRoommate.name;

// After
const name = user.linkedRoommate?.name ?? 'Unknown';
```

## Performance Considerations

- **Build Time**: TypeScript adds ~10-20% to build time (negligible for this project size)
- **Development**: Hot reload works the same as JavaScript
- **Bundle Size**: No change - TypeScript is compiled to JavaScript

## Resources

### TypeScript Documentation
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)

### Internal Documentation
- Type definitions: `frontend/src/types/`
- Migrated API service: `frontend/src/services/api.ts`
- This migration guide: `frontend/TYPESCRIPT_MIGRATION.md`

## Progress Tracking

### Phase Completion
- ✅ Phase 1: Infrastructure Setup (100%)
- ⏳ Phase 2: Service Layer Migration (0%)
- ⏳ Phase 3: Context Migration (0%)
- ⏳ Phase 4: Utility Functions (0%)
- ⏳ Phase 5: Component Migration (0%)
- ⏳ Phase 6: Strictness Increase (0%)

### File Conversion Status

**TypeScript Files**: 5
- ✅ `src/services/api.ts`
- ✅ `src/types/models.ts`
- ✅ `src/types/api.ts`
- ✅ `src/types/index.ts`
- ✅ `tsconfig.json`

**JavaScript Files Remaining**: ~15-20 components + contexts

**Overall Progress**: **~15%** complete

## Next Steps

1. **Install TypeScript dependencies** (if not already done):
   ```bash
   cd frontend
   npm install
   ```

2. **Run type check to verify setup**:
   ```bash
   npm run type-check
   ```

3. **Choose next migration target**:
   - Recommended: Start with `AuthContext.js` (high impact, medium effort)
   - Alternative: Convert simple utility functions first (low effort)

4. **Continue incremental migration**:
   - Convert 1-2 files per session
   - Test thoroughly after each conversion
   - Commit each conversion separately

## Notes for Future Developers

- **Coexistence**: JavaScript and TypeScript files work together seamlessly
- **No Rush**: Take time to understand TypeScript patterns
- **Incremental**: No need to convert everything at once
- **Type Safety**: When in doubt, add more specific types rather than using `any`
- **Testing**: Always run `npm run type-check` before committing TypeScript changes

---

**Last Updated**: 2025-10-12
**Maintained By**: Development Team
**Questions?**: See TypeScript resources or check existing `.ts` files for examples
