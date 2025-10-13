# Performance Management Assistant

This is a python based TUI (Text based User Interface) to assist with performance management in a corporate environment.  This application is a single user application to be used by a a manager of managers (multi-level) in order to do simple data input as to the performance ratings of their people, and to do some simple and roll-up reporting across level, manager, and manager of mangers to ensure adherance to the corporate distribution curve and to ensure that managers are consistently applying the performance ratings.

For the purposes of this documentation, the words Employee and Associate are synonomous. 


## Architecture

This is a single user python based Text User Input applciation.  This application uses:
- Textual - Main UI framework (forms, tables, navigation)
- Rich - Enhanced text formatting and simple displays
- Pandera - Data validation
- Pandas - Data manipulation and storage
- Click - Command-line argument parsing (if needed)
- SQLLite - used as a local database for storage
- SQLAlchemy and Alembic - Data abstraction layer and migrations

## Ket Data Models/Elements

### Associate
- Has a first name and a last name
- Has an Associate Level (defined below)
- Has a Manager (Also an Associate) -- This is done to be self referencing and allow for a multi-level hierarchy corporate reporting structure
- Has a logical field People Manager Indicator that is true if this person has subordinates assigned to them
- Has a Performance Rating (defined below)

### Associate Level
- The Associate level is their hierarchial position in the company
- Has a description
- Has a level indicator.  Lower numbers represent lower levels of the corporate hierarchy


### Performance Rating
- The performance rating is the rating that the Associate receives for the performance cycle
- Has a description
- Has a level indicator.  Lower numbers represent lower levels of performance.  Higher numbers represent higher numbers of performance.

## The application graphical interfaces will be split into areas.  Configuration, Data Input, and Reports

### Configuration
- A screen to perform CRUD operations on Associates.  This is used to enter the associates first and last name, and manager, but not their Performance Rating
- A screen to perform CRUD operations on Associate Levels
- A screen to perform CRUD operations on Performance Ratings. 

### Data Input
- Screens by Associate Level to input their performance rating.  This should make for easy entry by allowing all assoociates to be edited by level at the same time.  Editing this one employee at a time isn't efficient here.

### Reports
- A screen to calculate by level the overall percentage of Associates by performance rating (shown in a table) as well as a table showing the percentage of associates by performance rating by level.
