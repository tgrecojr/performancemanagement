# Data Model Implementation Overview

## Project Structure

```
performancemanagement/
├── alembic/                      # Database migrations
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── script.py.mako
├── src/
│   ├── models/                   # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py              # Base class for all models
│   │   ├── associate_level.py   # AssociateLevel model
│   │   ├── performance_rating.py # PerformanceRating model
│   │   └── associate.py         # Associate model
│   ├── database/                 # Database configuration
│   │   ├── __init__.py
│   │   └── config.py            # DB connection and session management
│   ├── ui/                       # Future: Textual UI components
│   └── reports/                  # Reporting logic
│       ├── __init__.py
│       └── distribution_calculator.py  # Performance distribution calculations
├── data/                         # SQLite database location (auto-created)
├── tests/                        # Future: Test files
├── alembic.ini                   # Alembic configuration
├── requirements.txt              # Python dependencies
├── test_models.py               # Model testing script
└── CLAUDE.md                     # Project specifications
```

## Data Models

### 1. AssociateLevel
**File**: `src/models/associate_level.py`

Represents hierarchical positions in the company.

**Fields**:
- `id` (Integer, PK): Primary key, auto-increment
- `description` (String(100), Unique): Level description (e.g., "Senior Manager")
- `level_indicator` (Integer, Unique): Numeric level (lower = lower in hierarchy)
- `max_percentage` (Float): Max % of employees allowed at this level (0-100)
- `exclude_from_distribution` (Boolean): If True, excludes this level from headcount denominator
  and rating distribution calculations (e.g., contractors, interns)

**Constraints**:
- `level_indicator` must be > 0
- `max_percentage` must be between 0-100
- Both `description` and `level_indicator` must be unique

**Relationships**:
- `associates`: One-to-Many with Associate (cascade delete)

---

### 2. PerformanceRating
**File**: `src/models/performance_rating.py`

Represents performance rating levels.

**Fields**:
- `id` (Integer, PK): Primary key, auto-increment
- `description` (String(100), Unique): Rating description (e.g., "Exceeds Expectations")
- `level_indicator` (Integer, Unique): Numeric level (lower = worse, higher = better)

**Constraints**:
- `level_indicator` must be > 0
- Both `description` and `level_indicator` must be unique

**Relationships**:
- `associates`: One-to-Many with Associate

---

### 3. Associate
**File**: `src/models/associate.py`

Represents employees/associates with self-referencing hierarchy.

**Fields**:
- `id` (Integer, PK): Primary key, auto-increment
- `first_name` (String(100)): First name
- `last_name` (String(100)): Last name
- `associate_level_id` (Integer, FK): Foreign key to AssociateLevel (RESTRICT on delete)
- `manager_id` (Integer, FK, Nullable): Self-referencing FK to Associate (SET NULL on delete)
- `performance_rating_id` (Integer, FK, Nullable): Foreign key to PerformanceRating (SET NULL on delete)
- `is_people_manager` (Boolean): True if has direct reports

**Relationships**:
- `associate_level`: Many-to-One with AssociateLevel
- `performance_rating`: Many-to-One with PerformanceRating (optional)
- `manager`: Many-to-One self-referencing (parent in hierarchy)
- `direct_reports`: One-to-Many self-referencing (children in hierarchy)

**Properties**:
- `full_name`: Computed property returning "first_name last_name"

**Foreign Key Behaviors**:
- Deleting an AssociateLevel is RESTRICTED if associates exist with that level
- Deleting a manager sets `manager_id` to NULL for their reports
- Deleting a PerformanceRating sets `performance_rating_id` to NULL

---

## Database Configuration

**File**: `src/database/config.py`

- **Database**: SQLite stored in `data/performance_management.db`
- **Engine**: SQLAlchemy 2.0+ with connection pooling
- **Session Management**: Factory pattern with `SessionLocal`

**Key Functions**:
- `init_db()`: Creates all tables (use once at startup)
- `get_session()`: Generator for dependency injection pattern
- `get_db()`: Direct session getter (remember to close)

---

## Indexes

For performance optimization, the following indexes are created:

- `ix_associates_manager_id`: Speed up manager lookups
- `ix_associates_associate_level_id`: Speed up level filtering
- `ix_associates_performance_rating_id`: Speed up rating queries
- `ix_associates_is_people_manager`: Speed up manager filtering

---

## Key Design Decisions

### 1. Self-Referencing Hierarchy
The `Associate` model uses `manager_id` to create a self-referencing relationship, enabling multi-level reporting structures:
```
CEO (no manager)
└── VP (manager: CEO)
    └── Manager (manager: VP)
        └── IC (manager: Manager)
```

### 2. Nullable Performance Ratings
`performance_rating_id` is nullable because:
- Associates are created before performance cycles
- Ratings are assigned separately via Data Input screens

### 3. Cascading Behaviors
- **RESTRICT on AssociateLevel**: Prevents accidental deletion of levels still in use
- **SET NULL on manager/rating**: Gracefully handles deletions without orphaning records
- **CASCADE on direct_reports**: SQLAlchemy-level cascade for relationship loading

### 4. Validation Constraints
Database-level CHECK constraints ensure data integrity:
- Level indicators must be positive
- Percentages must be 0-100
- Unique constraints on descriptions and level indicators

---

## Next Steps

Before proceeding to UI implementation, verify the models:

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Test the models**:
   ```bash
   python test_models.py
   ```

3. **Review the database schema**:
   - Check table structure in `data/performance_management.db`
   - Verify relationships work as expected
   - Test constraint enforcement

---

## Questions for Review

Before continuing, please confirm:

1. **Field completeness**: Do the models capture all required data?
2. **Relationship correctness**: Is the self-referencing hierarchy appropriate?
3. **Constraint validity**: Are the CHECK constraints and foreign key behaviors correct?
4. **Missing fields**: Should we add:
   - Timestamps (created_at, updated_at)?
   - Soft delete flags?
   - Additional metadata fields?
5. **Performance rating assignment**: Should there be a separate table for performance cycles/periods?
6. **Associate Level percentage**: Should we enforce the max_percentage constraint at the application level?

Let me know if you'd like any changes to the models before we proceed!
