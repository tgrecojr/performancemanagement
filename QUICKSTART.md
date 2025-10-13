# Quick Start Guide

## Setup and Run (First Time)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python run.py
   ```

The database will be automatically created on first run.

## Testing the Performance Ratings Screen

### Step 1: Launch the App
```bash
python run.py
```

You'll see the main menu with several options.

### Step 2: Open Performance Ratings
- Click "Performance Ratings" button, or
- Press `1` (if numbered), or
- Use Tab to navigate and Enter to select

### Step 3: Add Performance Ratings

Press `A` or click "Add" to create ratings. Here are some examples:

**Rating 1:**
- Description: `Needs Improvement`
- Level Indicator: `1`

**Rating 2:**
- Description: `Meets Expectations`
- Level Indicator: `2`

**Rating 3:**
- Description: `Exceeds Expectations`
- Level Indicator: `3`

**Rating 4:**
- Description: `Outstanding`
- Level Indicator: `4`

### Step 4: Test CRUD Operations

**Edit a Rating:**
1. Use arrow keys to select a row
2. Press `E` or click "Edit"
3. Modify the description or level
4. Click "Save"

**Delete a Rating:**
1. Select a row
2. Press `D` or click "Delete"
3. The rating will be deleted (if not in use)

**Try Invalid Data:**
- Add a rating with duplicate description → Error message
- Add a rating with duplicate level → Error message
- Add a rating with level 0 or negative → Validation error
- Leave fields empty → Validation error

### Step 5: Navigation

- Press `ESC` or click "Back" to return to main menu
- Press `Q` to quit the application

## Keyboard Shortcuts Cheat Sheet

### Global
- `Q` - Quit application
- `ESC` - Go back/Cancel

### Performance Ratings Screen
- `A` - Add new rating
- `E` - Edit selected rating
- `D` - Delete selected rating
- `R` - Refresh table
- `↑↓` - Navigate table rows
- `Tab` - Navigate between UI elements

## Common Issues

### Import Errors
If you get `ModuleNotFoundError`, make sure you're running from the project root:
```bash
cd /Users/tgrecojr/code/performancemanagement
python run.py
```

### Database Errors
If the database gets corrupted, delete it and restart:
```bash
rm -rf data/
python run.py
```

### Screen Layout Issues
If the UI looks broken, try resizing your terminal to at least 80x24 characters.

## What's Working

✅ Main menu navigation
✅ Performance Ratings CRUD (Create, Read, Update, Delete)
✅ Form validation
✅ Database persistence
✅ Keyboard shortcuts
✅ Error handling and notifications

## What's Next

The following screens are placeholders (show "Coming soon" message):
- Associate Levels configuration
- Associates configuration
- Data Input screens
- Distribution reports

These will be implemented next following the same pattern as Performance Ratings.
