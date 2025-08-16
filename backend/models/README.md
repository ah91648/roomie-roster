# RoomieRoster SQLAlchemy Models

This directory contains comprehensive SQLAlchemy models for the RoomieRoster household chore management application. These models provide a database-backed replacement for the existing JSON file-based data storage.

## Overview

The models are designed to replicate and enhance the functionality of the existing `DataHandler` class while providing the benefits of a relational database:

- **Data integrity** through foreign key constraints and validation
- **Complex queries** using SQLAlchemy's ORM capabilities  
- **Transaction support** for atomic operations
- **Schema migrations** for database evolution
- **Better performance** for large datasets
- **Concurrent access** support

## Architecture

### Core Models

1. **Roommate** - Represents household members
2. **Chore** - Represents household tasks with frequency and point values
3. **SubChore** - Represents sub-tasks within chores
4. **Assignment** - Represents chore assignments to roommates
5. **SubChoreCompletion** - Tracks completion of sub-tasks within assignments

### Shopping and Request Models

6. **ShoppingItem** - Items on the shared shopping list
7. **PurchaseRequest** - Purchase requests requiring roommate approval
8. **Approval** - Individual approvals/declines for purchase requests

### Scheduling Models

9. **LaundrySlot** - Laundry time slot reservations
10. **BlockedTimeSlot** - Blocked time periods preventing scheduling

### System Models

11. **ApplicationState** - Application state and metadata storage

## Key Features

### Model Validation
All models include comprehensive validation:
```python
# Automatic validation on save
chore = Chore(name="", points=-1)  # Raises validation errors
```

### Relationships
Models use SQLAlchemy relationships for easy navigation:
```python
# Get all assignments for a roommate
assignments = roommate.assignments.filter_by(is_active=True).all()

# Get chore with sub-chores
chore = session.query(Chore).options(joinedload(Chore.sub_chores)).first()
```

### Computed Properties
Models include hybrid properties for common calculations:
```python
assignment.is_overdue  # True if past due date
assignment.days_until_due  # Days until due (negative if overdue)
shopping_item.price_difference  # Difference between actual and estimated price
```

### Rich Methods
Models provide methods that encapsulate business logic:
```python
# Mark assignment as completed (awards points to roommate)
assignment.mark_completed()

# Toggle sub-chore completion
sub_chore.toggle_completion(assignment)

# Check for scheduling conflicts
conflicts = laundry_slot.check_conflicts()
```

## Usage

### Basic Setup

```python
from flask import Flask
from backend.models import setup_database, create_database_tables

app = Flask(__name__)

# Setup database configuration
db = setup_database(app, 'development')

# Create tables
create_database_tables(app)
```

### Using the Data Access Layer

The `DatabaseDataHandler` class provides a drop-in replacement for the existing `DataHandler`:

```python
from backend.models.data_access import DatabaseDataHandler

# Initialize (uses db.session by default)
data_handler = DatabaseDataHandler()

# Use exactly like the original DataHandler
roommates = data_handler.get_roommates()
chores = data_handler.get_chores()

# Add new data
new_chore = data_handler.add_chore({
    'name': 'Clean Kitchen',
    'frequency': 'daily',
    'type': 'random',
    'points': 5,
    'sub_chores': [
        {'name': 'Wipe counters'},
        {'name': 'Clean sink'},
        {'name': 'Sweep floor'}
    ]
})
```

### Direct Model Usage

For more advanced operations, use models directly:

```python
from backend.models import Roommate, Chore, Assignment

# Create new roommate
roommate = Roommate(name="Alice", current_cycle_points=0)
db.session.add(roommate)
db.session.commit()

# Complex queries
overdue_assignments = db.session.query(Assignment).filter(
    Assignment.is_active == True,
    Assignment.due_date < datetime.utcnow()
).all()

# Get roommate statistics
stats = db.session.query(
    Roommate.name,
    func.count(Assignment.id).label('total_assignments'),
    func.sum(Assignment.points).label('total_points')
).join(Assignment).group_by(Roommate.id).all()
```

## Migration from JSON

Use the migration utility to convert existing JSON data:

```python
from backend.models.migration import run_migration

# Run full migration (creates backup automatically)
success = run_migration(app, json_data_dir='data', create_backup=True)

if success:
    print("Migration completed successfully!")
else:
    print("Migration failed - check logs for details")
```

The migration process:
1. **Creates a backup** of existing JSON files
2. **Validates data** before migration
3. **Preserves relationships** between entities
4. **Maintains data integrity** through transactions
5. **Provides detailed logging** of the process
6. **Validates results** by comparing record counts

## Configuration

### Database Configuration

The system supports multiple database configurations:

```python
# Development (SQLite)
SQLALCHEMY_DATABASE_URI = 'sqlite:///data/roomieroster.db'

# Production (PostgreSQL on Render/Heroku)
DATABASE_URL = 'postgresql://user:pass@host:port/database'

# Testing (In-memory SQLite)
SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

### Environment Setup

Set the Flask environment to control configuration:

```bash
# Development
export FLASK_ENV=development

# Production  
export FLASK_ENV=production

# Testing
export FLASK_ENV=testing
```

## API Compatibility

The `DatabaseDataHandler` maintains complete API compatibility with the existing `DataHandler`:

### Supported Methods

**Chores:**
- `get_chores()` → `List[Dict]`
- `add_chore(chore_data)` → `Dict`
- `update_chore(chore_id, chore_data)` → `Dict`
- `delete_chore(chore_id)` → `None`

**Sub-chores:**
- `add_sub_chore(chore_id, name)` → `Dict`
- `update_sub_chore(chore_id, sub_chore_id, name)` → `Dict`
- `delete_sub_chore(chore_id, sub_chore_id)` → `None`
- `toggle_sub_chore_completion(chore_id, sub_chore_id, assignment_index)` → `Dict`
- `get_sub_chore_progress(chore_id, assignment_index)` → `Dict`

**Roommates:**
- `get_roommates()` → `List[Dict]`
- `add_roommate(roommate_data)` → `Dict`
- `update_roommate(roommate_id, roommate_data)` → `Dict`
- `delete_roommate(roommate_id)` → `None`

**Assignments:**
- `get_current_assignments()` → `List[Dict]`
- `save_current_assignments(assignments)` → `None`

**Shopping List:**
- `get_shopping_list()` → `List[Dict]`
- `add_shopping_item(item_data)` → `Dict`
- `update_shopping_item(item_id, item_data)` → `Dict`
- `delete_shopping_item(item_id)` → `None`
- `mark_item_purchased(item_id, purchased_by, purchased_by_name, actual_price, notes)` → `Dict`
- `get_shopping_list_by_status(status)` → `List[Dict]`
- `get_purchase_history(days)` → `List[Dict]`

**Purchase Requests:**
- `get_requests()` → `List[Dict]`
- `add_request(request_data)` → `Dict`
- `update_request(request_id, request_data)` → `Dict`
- `delete_request(request_id)` → `None`
- `approve_request(request_id, approval_data)` → `Dict`
- `get_requests_by_status(status)` → `List[Dict]`
- `get_pending_requests_for_user(user_id)` → `List[Dict]`

**Laundry Scheduling:**
- `get_laundry_slots()` → `List[Dict]`
- `add_laundry_slot(slot_data)` → `Dict`
- `update_laundry_slot(slot_id, slot_data)` → `Dict`
- `delete_laundry_slot(slot_id)` → `None`
- `check_laundry_slot_conflicts(date, time_slot, machine_type, exclude_slot_id)` → `List[Dict]`
- `mark_laundry_slot_completed(slot_id, actual_loads, completion_notes)` → `Dict`

**Blocked Time Slots:**
- `get_blocked_time_slots()` → `List[Dict]`
- `add_blocked_time_slot(slot_data)` → `Dict`
- `update_blocked_time_slot(slot_id, slot_data)` → `Dict`
- `delete_blocked_time_slot(slot_id)` → `None`
- `check_blocked_time_conflicts(date, time_slot, exclude_slot_id)` → `List[Dict]`

**Application State:**
- `get_state()` → `Dict`
- `save_state(state)` → `None`
- `update_last_run_date(date_str)` → `None`
- `update_predefined_chore_state(chore_id, roommate_id)` → `None`

## Testing

### Unit Tests

Test individual models:

```python
def test_chore_validation():
    with pytest.raises(ValueError):
        chore = Chore(name="", points=0)  # Invalid: empty name and zero points

def test_assignment_completion():
    assignment = create_test_assignment()
    original_points = assignment.roommate.current_cycle_points
    
    assignment.mark_completed()
    
    assert not assignment.is_active
    assert assignment.completed_at is not None
    assert assignment.roommate.current_cycle_points == original_points + assignment.points
```

### Integration Tests

Test the data access layer:

```python
def test_data_handler_compatibility():
    handler = DatabaseDataHandler()
    
    # Test adding chore with sub-chores
    chore_data = {
        'name': 'Test Chore',
        'frequency': 'daily',
        'type': 'random',
        'points': 5,
        'sub_chores': [{'name': 'Sub-task 1'}, {'name': 'Sub-task 2'}]
    }
    
    result = handler.add_chore(chore_data)
    assert result['name'] == 'Test Chore'
    assert len(result['sub_chores']) == 2
```

### Migration Tests

Test the migration process:

```python
def test_migration_preserves_data():
    # Setup JSON data
    setup_test_json_data()
    
    # Run migration
    success = run_migration(test_app)
    assert success
    
    # Verify data integrity
    assert db.session.query(Roommate).count() == 4
    assert db.session.query(Chore).count() == 6
    # ... more assertions
```

## Performance Considerations

### Query Optimization

Use SQLAlchemy's query optimization features:

```python
# Eager loading to avoid N+1 queries
chores = db.session.query(Chore).options(
    joinedload(Chore.sub_chores),
    joinedload(Chore.assignments)
).all()

# Selective loading
assignments = db.session.query(Assignment).options(
    load_only(Assignment.id, Assignment.chore_name, Assignment.due_date)
).filter_by(is_active=True).all()
```

### Indexing

Key indexes are automatically created:

```python
# Automatic indexes on:
- Primary keys (id fields)
- Foreign keys (roommate_id, chore_id, etc.)
- Unique constraints (roommate.name, roommate.google_id)

# Consider adding custom indexes for frequent queries:
# db.Index('idx_assignment_due_date', Assignment.due_date)
# db.Index('idx_shopping_status_date', ShoppingItem.status, ShoppingItem.date_added)
```

### Connection Management

Configure connection pooling for production:

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 5,          # Number of connections in pool
    'max_overflow': 10,      # Additional connections beyond pool_size
    'pool_recycle': 300,     # Recycle connections after 5 minutes
    'pool_pre_ping': True    # Validate connections before use
}
```

## Deployment

### Requirements

Add to `requirements.txt`:

```
Flask-SQLAlchemy==3.0.5
SQLAlchemy==2.0.23
alembic==1.13.0          # For database migrations (optional)
psycopg2-binary==2.9.7   # For PostgreSQL (production)
```

### Environment Variables

Set these for production deployment:

```bash
# Database URL for production (PostgreSQL recommended)
DATABASE_URL=postgresql://username:password@host:port/database

# Flask environment
FLASK_ENV=production

# Other RoomieRoster config
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
FLASK_SECRET_KEY=your_secret_key
```

### Database Migration Strategy

For production deployment:

1. **Run migration script** to convert JSON data
2. **Test thoroughly** with the new database
3. **Keep JSON backup** until confident in stability
4. **Monitor performance** and optimize queries as needed

### Rollback Plan

If issues arise:

1. **Stop the application**
2. **Restore from JSON backup** using migration utilities
3. **Investigate and fix issues**
4. **Re-run migration** when ready

## Troubleshooting

### Common Issues

**Migration fails:**
- Check JSON data validity
- Ensure all foreign key relationships exist
- Review migration logs for specific errors

**Performance issues:**
- Add database indexes for frequent queries
- Use eager loading to avoid N+1 queries
- Consider query optimization

**Data integrity errors:**
- Verify foreign key constraints
- Check for duplicate data
- Review model validation rules

**Connection issues:**
- Verify database URL configuration
- Check connection pool settings
- Ensure database server is accessible

### Debugging

Enable SQL query logging:

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

Use Flask-SQLAlchemy's debug features:

```python
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_RECORD_QUERIES'] = True
```

## Future Enhancements

### Database Migrations

Consider adding Alembic for schema migrations:

```python
# Initialize Alembic
alembic init migrations

# Generate migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head
```

### Advanced Features

Potential enhancements:
- **Audit logging** for data changes
- **Soft deletes** instead of hard deletes
- **Data archiving** for old assignments
- **Performance monitoring** with query metrics
- **Database replication** for high availability
- **Full-text search** for chores and items

### API Extensions

Additional API methods:
- Bulk operations for better performance
- Advanced filtering and sorting
- Pagination for large datasets
- Aggregation queries for statistics
- Custom query builders

## Support

For questions or issues with the SQLAlchemy models:

1. **Check the migration logs** for specific error details
2. **Review the model documentation** in source code
3. **Test with sample data** using the provided utilities
4. **Compare with JSON DataHandler** for expected behavior

The models are designed to be a drop-in replacement for the existing JSON-based system while providing enhanced capabilities for the future growth of RoomieRoster.