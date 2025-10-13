# Performance Management System

A Text User Interface (TUI) application for managing employee performance ratings in a corporate environment with advanced distribution management and bulk import capabilities.

## Features

- Manage performance ratings with flexible distribution buckets
- Track employees and their hierarchical reporting structure
- Bulk import associates from CSV files
- Input performance ratings for associates
- Generate comprehensive distribution reports with exclusion rules
- Configure distribution targets with min/max percentages
- Support for excluded ratings (e.g., "Too New to Rate")

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. The database will be automatically created on first run.

## Running the Application

```bash
python run.py
```

Or directly:
```bash
python -m src.ui.main_app
```

## Usage

### Main Menu

The application opens to a main menu with three sections:

1. **Configuration**
   - Performance Ratings: Manage rating definitions with distribution settings
   - Distribution Buckets: Configure min/max targets for rating groups
   - Associate Levels: Manage organizational hierarchy levels
   - Associates: Manage employees and their reporting structure

2. **Data Input**
   - Import Associates (CSV): Bulk load associates with hierarchy from CSV
   - Enter Performance Ratings: Bulk assignment of ratings to associates by level

3. **Reports**
   - Distribution Reports: Comprehensive distribution analysis with bucket targets

### Configuration Screens

#### Performance Ratings Configuration

**Keyboard Shortcuts:**
- `A` - Add a new performance rating
- `E` - Edit selected rating
- `D` - Delete selected rating
- `R` - Refresh the data table
- `ESC` - Go back to main menu
- `Q` - Quit application

**Features:**
- View all performance rating definitions in a sortable table
- Add new ratings with description and level indicator
- **NEW:** Assign ratings to distribution buckets for min/max target management
- **NEW:** Mark ratings as excluded from distribution calculations
- Edit existing ratings
- Delete ratings (protected if in use by associates)
- Validation ensures unique descriptions and level indicators
- Table shows which bucket each rating belongs to and exclusion status

**Level Indicator:** Lower numbers represent lower performance, higher numbers represent better performance (e.g., 1=Needs Improvement, 5=Outstanding).

**Distribution Settings:**
- **Excluded from Distribution:** Check to exclude ratings like "Too New to Rate" from distribution calculations
- **Distribution Bucket:** Assign to a bucket for min/max percentage management (optional)

#### Distribution Buckets Configuration

**Keyboard Shortcuts:**
- `A` - Add a new distribution bucket
- `E` - Edit selected bucket
- `D` - Delete selected bucket
- `V` - Validate bucket configuration
- `R` - Refresh the data table
- `ESC` - Go back to main menu

**Features:**
- **NEW:** Create distribution buckets that group multiple performance ratings
- Set minimum and maximum percentage targets for each bucket
- Configure sort order for report display
- View how many ratings are assigned to each bucket
- Built-in validation to check if configuration is achievable
- Delete protection for buckets with assigned ratings

**Use Case:**
Group multiple ratings together for distribution management. For example:
- "High Performers" bucket (15-25%): Contains "Exceptional" and "Very Strong" ratings
- "Core Contributors" bucket (60-75%): Contains "Meets Expectations" rating
- "Development Needed" bucket (5-15%): Contains "Needs Improvement" rating

#### Associate Levels Configuration

**Keyboard Shortcuts:**
- `A` - Add a new associate level
- `E` - Edit selected level
- `D` - Delete selected level
- `R` - Refresh the data table
- `ESC` - Go back to main menu

**Features:**
- Manage organizational hierarchy levels
- Add, edit, and delete levels
- Delete protection for levels in use
- Unique descriptions and level indicators enforced

**Level Indicator:** Lower numbers represent lower organizational levels (e.g., 1=Individual Contributor, 3=Director).

#### Associates Configuration

**Keyboard Shortcuts:**
- `A` - Add a new associate
- `E` - Edit selected associate
- `D` - Delete selected associate
- `C` - **NEW:** Clear all associates (with warning)
- `R` - Refresh the data table
- `ESC` - Go back to main menu

**Features:**
- Manage employee records with first name, last name, level, and manager
- Self-referencing manager hierarchy support
- Automatic people manager indicator tracking
- Delete protection for associates with direct reports
- **NEW:** Clear All button to reset all associates (useful before CSV import)
- Performance ratings assigned separately in Data Input screen

### Data Input Screens

#### Import Associates (CSV)

**NEW FEATURE** - Bulk import associates with their hierarchy from a CSV file.

**Features:**
- Import associates with first name, last name, level, and manager information
- Automatic manager relationship building
- Smart people manager detection
- Update existing associates option
- Comprehensive validation with helpful error messages
- Generate sample CSV template with example data
- Detailed import results showing created/updated/skipped counts

**CSV Format:**
```csv
first_name,last_name,level,manager_first_name,manager_last_name,is_people_manager
John,CEO,Executive,,,true
Jane,Director,Director,John,CEO,true
Bob,Manager,Manager,Jane,Director,true
Alice,Employee,Individual Contributor,Bob,Manager,false
```

**Important Notes:**
- Level names must exactly match existing Associate Levels in the system
- Managers must be defined before their direct reports in the CSV
- Top-level manager should have empty manager fields
- Both manager first and last name must be provided together, or both left empty
- **is_people_manager** is optional (defaults to false if not provided)
  - Accepts: true/yes/1/y (case-insensitive) for True
  - Any other value or empty is treated as False
  - Automatically set to True for anyone with direct reports

**Workflow:**
1. Click "Generate Sample CSV" to create a template
2. Edit the CSV with your data (matching your Associate Levels)
3. Enter the file path in the input field
4. Optionally check "Update existing associates if found"
5. Click "Import CSV" to process
6. Review detailed results showing successes, warnings, and errors

#### Enter Performance Ratings

**Keyboard Shortcuts:**
- `S` - Save all pending changes
- `R` - Refresh (discards unsaved changes)
- `ESC` - Go back to main menu

**Features:**
- **Level Filtering:** Filter associates by organizational level or view all
- **Bulk Assignment:** Queue up multiple rating changes before saving
- **Visual Feedback:** See current and pending new ratings in table
- **Change Tracking:** Pending changes indicator shows number of unsaved assignments
- **Rating Selection Modal:** Click any associate row to open an easy rating selector
- **Safety Features:** Warnings when leaving with unsaved changes

**Workflow:**
1. Optionally filter by associate level to focus on specific groups
2. Click on any associate row to assign/change their rating
3. Select a rating from the modal (or clear the rating)
4. Repeat for as many associates as needed
5. Press "Save All [S]" to commit all changes at once

### Reports

#### Distribution Reports

**Features:**
- **NEW:** Comprehensive multi-section distribution analysis
- **NEW:** Headcount summary showing all exclusions
- **NEW:** Distribution bucket analysis with target ranges
- **NEW:** Visual status indicators (✓ Within, ↓ Below Min, ↑ Above Max)
- **NEW:** Automatic exclusion of top-level manager and excluded ratings
- Individual rating percentages (for included ratings only)
- Excluded associates visibility section
- Distribution breakdown by organizational level
- Helps ensure consistent application of ratings and adherence to distribution targets

**Report Sections:**

1. **Headcount Summary**
   - Total associates count
   - Top-level manager (excluded)
   - Excluded ratings count (e.g., "Too New")
   - Unrated associates
   - Final count included in distribution

2. **Distribution Bucket Analysis**
   - Each bucket's actual percentage vs. min/max targets
   - Status indicators showing if within target
   - Rating breakdown within each bucket
   - Warnings for out-of-range buckets

3. **Individual Rating Distribution**
   - Percentage breakdown for each rating (included only)
   - Total adds to 100% of included associates

4. **Excluded Associates**
   - Top-level manager visibility
   - Excluded ratings breakdown
   - Unrated count

## Advanced Features

### Distribution Bucket System

The application supports a flexible distribution bucket system that allows you to:

1. **Group Multiple Ratings:** Combine ratings like "Exceptional" and "Very Strong" into one "High Performers" bucket
2. **Set Min/Max Targets:** Define acceptable percentage ranges (e.g., 15-25%) for each bucket
3. **Automatic Validation:** System warns when actual distribution falls outside targets
4. **No Hardcoding:** All configuration is data-driven through the UI

### Exclusion Rules

The system automatically handles exclusions:

1. **Top-Level Manager:** The associate with no manager is automatically excluded
2. **Excluded Ratings:** Ratings marked as "excluded from distribution" (like "Too New to Rate")
3. **Unrated Associates:** Associates without ratings are tracked but excluded
4. **Visibility:** All excluded associates shown separately in reports for transparency

### CSV Import Tips

- Use the "Generate Sample CSV" button to create a correctly formatted template
- Ensure level names match exactly (case-insensitive)
- List managers before their reports in the CSV
- Use consistent naming (the system matches by first and last name)
- Check import results for any warnings or errors
- Use "Clear All [C]" before importing to start fresh

## Project Structure

```
performancemanagement/
├── src/
│   ├── models/          # SQLAlchemy database models
│   │   ├── associate.py
│   │   ├── associate_level.py
│   │   ├── performance_rating.py
│   │   └── distribution_bucket.py (NEW)
│   ├── database/        # Database configuration
│   ├── ui/              # Textual TUI screens
│   │   ├── main_app.py
│   │   ├── performance_ratings_screen.py
│   │   ├── distribution_buckets_screen.py (NEW)
│   │   ├── associate_levels_screen.py
│   │   ├── associates_screen.py
│   │   ├── csv_import_screen.py (NEW)
│   │   ├── rating_input_screen.py
│   │   └── distribution_report_screen.py
│   ├── reports/         # Reporting logic
│   │   └── distribution_calculator.py (ENHANCED)
│   └── utils/           # Utility functions (NEW)
│       ├── csv_importer.py
│       └── data_management.py
├── alembic/             # Database migrations
│   └── versions/
│       ├── 001_initial_schema.py
│       └── 002_add_distribution_buckets.py (NEW)
├── data/                # SQLite database (auto-created)
├── associates_template.csv  # Sample CSV template (NEW)
├── run.py               # Application entry point
└── requirements.txt     # Python dependencies
```

## Testing

### Test Scripts

Run the test scripts to verify functionality:

```bash
# Test basic models
python test_models.py

# Test CSV import functionality
python test_csv_import.py

# Test exclusion logic
python test_exclusion_logic.py
```

### Testing CSV Import

1. Run the test script to see CSV import in action:
```bash
python test_csv_import.py
```

2. Or use the sample template included in the project:
```bash
# Open associates_template.csv and edit with your data
# Then import through the UI
```

## Database

The application uses SQLite stored in `performance_management.db`.

### Database Migrations

The application uses Alembic for database migrations:

```bash
# Check current migration version
alembic current

# Upgrade to latest version
alembic upgrade head

# Downgrade one version
alembic downgrade -1
```

### Reset Database

To reset the database completely:
1. Delete `performance_management.db`
2. Restart the application (database will be recreated)

## Development Status

### Completed Features
- ✅ Database models and migrations
- ✅ **NEW:** Distribution bucket system with min/max targets
- ✅ **NEW:** Performance rating exclusion from distribution
- ✅ **NEW:** CSV bulk import for associates
- ✅ **NEW:** Clear all associates functionality
- ✅ Configuration Screens:
  - ✅ Performance Ratings CRUD with distribution settings
  - ✅ **NEW:** Distribution Buckets CRUD
  - ✅ Associate Levels CRUD
  - ✅ Associates CRUD with clear all
- ✅ Data Input Screens:
  - ✅ **NEW:** CSV Import with validation and error handling
  - ✅ Bulk Performance Rating Assignment by Level
- ✅ Reports:
  - ✅ **ENHANCED:** Comprehensive Distribution Reports with:
    - Headcount breakdown
    - Bucket analysis with targets
    - Status indicators
    - Exclusion visibility

### Current State
All core functionality is implemented and production-ready. The application provides a complete workflow for:
1. Configuring rating scales, distribution targets, and organizational hierarchy
2. Bulk importing employees with hierarchy from CSV
3. Managing employee records efficiently
4. Assigning performance ratings in bulk
5. Analyzing rating distributions with automatic exclusions
6. Monitoring adherence to distribution targets

## Documentation

- `CLAUDE.md` - Project specifications and guidelines
- `EXCLUSIONS.md` - Distribution exclusion rules and requirements
- `IMPLEMENTATION_PROPOSAL.md` - Detailed distribution system design
- `associates_template.csv` - Sample CSV import template

## Technologies

- **Textual** - Modern TUI framework for rich terminal interfaces
- **SQLAlchemy** - Powerful database ORM
- **Alembic** - Database migration management
- **SQLite** - Lightweight local database
- **Rich** - Advanced terminal formatting
- **Pandas** - Data manipulation
- **Pandera** - Data validation
- **Python 3.13** - Latest Python features

## Contributing

This is a single-user application designed for manager-of-managers use in corporate performance management cycles. All configuration is data-driven to avoid hardcoding of business rules.

## License

Internal corporate use.
