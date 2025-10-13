# Performance Management System

A Text User Interface (TUI) application for managing employee performance ratings in a corporate environment.

## Features

- Manage performance ratings and associate levels
- Track employees and their hierarchical reporting structure
- Input performance ratings for associates
- Generate distribution reports across levels and managers

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
   - Performance Ratings: Manage rating definitions (e.g., "Exceeds Expectations", "Meets Expectations")
   - Associate Levels: Manage organizational hierarchy levels (e.g., "Individual Contributor", "Manager", "Director")
   - Associates: Manage employees and their reporting structure

2. **Data Input**
   - Enter Performance Ratings: Bulk assignment of ratings to associates by level

3. **Reports**
   - Distribution Reports: View performance rating distribution by level and across the organization

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
- Edit existing ratings
- Delete ratings (protected if in use by associates)
- Validation ensures unique descriptions and level indicators

**Level Indicator:** Lower numbers represent lower performance, higher numbers represent better performance (e.g., 1=Needs Improvement, 5=Outstanding).

#### Associate Levels Configuration

**Keyboard Shortcuts:**
- `A` - Add a new associate level
- `E` - Edit selected level
- `D` - Delete selected level
- `R` - Refresh the data table
- `ESC` - Go back to main menu
- `Q` - Quit application

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
- `R` - Refresh the data table
- `ESC` - Go back to main menu
- `Q` - Quit application

**Features:**
- Manage employee records with first name, last name, level, and manager
- Self-referencing manager hierarchy support
- Automatic people manager indicator tracking
- Delete protection for associates with direct reports
- Performance ratings assigned separately in Data Input screen

### Data Input Screen

#### Enter Performance Ratings

**Keyboard Shortcuts:**
- `S` - Save all pending changes
- `R` - Refresh (discards unsaved changes)
- `ESC` - Go back to main menu
- `Q` - Quit application

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

This screen enables efficient bulk entry by allowing you to queue multiple rating assignments before saving, and the level filter helps you work through the organization systematically.

### Reports

#### Distribution Reports

**Features:**
- Overall performance rating distribution across all associates
- Rating distribution breakdown by organizational level
- Percentage calculations for distribution curve analysis
- Helps ensure consistent application of ratings across managers and levels

## Project Structure

```
performancemanagement/
├── src/
│   ├── models/          # SQLAlchemy database models
│   ├── database/        # Database configuration
│   ├── ui/              # Textual TUI screens
│   └── reports/         # Reporting logic
├── data/                # SQLite database (auto-created)
├── alembic/             # Database migrations
├── run.py               # Application entry point
└── requirements.txt     # Python dependencies
```

## Testing the Models

Run the test scripts to verify the database models:

```bash
# Test basic models
python test_models.py

# Test exclusion logic for contractors/interns
python test_exclusion_logic.py
```

## Database

The application uses SQLite stored in `data/performance_management.db`.

To reset the database, simply delete the `data/` directory and restart the application.

## Development Status

### Completed Features
- ✅ Database models and migrations
- ✅ Configuration Screens:
  - ✅ Performance Ratings CRUD screen
  - ✅ Associate Levels CRUD screen
  - ✅ Associates CRUD screen
- ✅ Data Input Screens:
  - ✅ Bulk Performance Rating Assignment by Level
- ✅ Reports:
  - ✅ Distribution Reports (overall and by level)

### Current State
All core functionality is implemented and ready for use. The application provides a complete workflow for:
1. Configuring rating scales and organizational hierarchy
2. Managing employee records
3. Efficiently assigning performance ratings
4. Analyzing rating distributions

## Documentation

- `CLAUDE.md` - Project specifications
- `MODEL_OVERVIEW.md` - Database model documentation
- `EXCLUSION_LOGIC.md` - Explanation of excluded levels feature
- `REFACTORING_SUMMARY.md` - Recent design changes

## Technologies

- **Textual** - Modern TUI framework
- **SQLAlchemy** - Database ORM
- **SQLite** - Local database
- **Rich** - Terminal formatting
- **Pandas** - Data manipulation
- **Pandera** - Data validation
