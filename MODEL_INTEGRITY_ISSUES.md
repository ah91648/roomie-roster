# Model Integrity Analysis - Zeith Productivity Features

## Critical Inconsistencies Found

### 1. PomodoroSession → TodoItem Relationship Mismatch

**models.py (line 1109):**
```python
todo = db.relationship('TodoItem', backref='pomodoro_sessions', foreign_keys='PomodoroSession.todo_id')
```

**database_models.py (line 455):**
```python
todo = relationship("TodoItem", backref="linked_pomodoro_sessions", foreign_keys=[todo_id])
```

**Impact:**
- TodoItem instances will have **different attribute names** for accessing Pomodoro sessions
- Code using `todo.pomodoro_sessions` will work with models.py but fail with database_models.py
- Code using `todo.linked_pomodoro_sessions` will work with database_models.py but fail with models.py

**Recommended Fix:** Standardize to `pomodoro_sessions` (more intuitive name)

---

### 2. TodoItem → Chore Relationship Mismatch

**models.py (line 1243):**
```python
chore = db.relationship('Chore', backref='todo_items')
```

**database_models.py (line 497):**
```python
chore = relationship("Chore", backref="linked_todos")
```

**Impact:**
- Chore instances will have **different attribute names** for accessing linked todos
- Code using `chore.todo_items` will work with models.py but fail with database_models.py
- Code using `chore.linked_todos` will work with database_models.py but fail with models.py

**Recommended Fix:** Standardize to `linked_todos` (matches existing pattern with `linked_pomodoro_sessions`)

---

### 3. Foreign Key Syntax Inconsistency

**models.py:**
- Uses string format: `foreign_keys='PomodoroSession.todo_id'`

**database_models.py:**
- Uses list format: `foreign_keys=[todo_id]`

**Impact:**
- Both are valid SQLAlchemy syntax, but inconsistency makes code harder to maintain
- The list format is preferred in modern SQLAlchemy

**Recommended Fix:** Standardize to list format: `foreign_keys=[PomodoroSession.todo_id]`

---

## Verification Status

✅ **Correct:**
- Table names match (`pomodoro_sessions`, `todo_items`, `mood_entries`, `analytics_snapshots`)
- Primary keys match (all use `id = Column(Integer, primary_key=True)`)
- Roommate foreign keys match
- Basic field types match

⚠️ **Needs Fixing:**
- Relationship backref names (2 inconsistencies found)
- Foreign key syntax (1 inconsistency found)

---

## Next Steps

1. **Decision Required:** Which model file is the source of truth?
   - `models.py` uses Flask-SQLAlchemy (`db.Column`, `db.relationship`)
   - `database_models.py` uses vanilla SQLAlchemy (`Column`, `relationship`)
   - App uses `DatabaseDataHandler` which imports from `database_models.py`

2. **Recommended Approach:**
   - Fix `database_models.py` to match `models.py` backref names
   - Update foreign key syntax to list format in both files
   - Run migration to ensure no database schema issues

3. **Testing Priority:**
   - Cannot proceed with unit tests until these inconsistencies are resolved
   - Any code using these relationships will have undefined behavior
