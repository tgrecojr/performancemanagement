"""CSV import utility for bulk loading associates."""
import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models import Associate, AssociateLevel


@dataclass
class ImportResult:
    """Result of CSV import operation."""
    success: bool
    created_count: int
    updated_count: int
    skipped_count: int
    errors: List[str]
    warnings: List[str]


@dataclass
class AssociateRow:
    """Represents a single row from the CSV."""
    row_number: int
    first_name: str
    last_name: str
    level: str
    manager_first_name: Optional[str]
    manager_last_name: Optional[str]
    is_people_manager: bool = False  # Default to False if not provided


def validate_csv_file(file_path: str) -> Tuple[bool, List[str]]:
    """
    Validate CSV file structure and format.

    Args:
        file_path: Path to CSV file

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Check required columns
            required_columns = {'first_name', 'last_name', 'level'}
            optional_columns = {'manager_first_name', 'manager_last_name', 'is_people_manager'}
            all_columns = required_columns | optional_columns

            if not reader.fieldnames:
                errors.append("CSV file is empty or has no header row")
                return False, errors

            # Normalize column names (strip whitespace, lowercase)
            normalized_fields = {col.strip().lower() for col in reader.fieldnames}

            missing_columns = required_columns - normalized_fields
            if missing_columns:
                errors.append(f"Missing required columns: {', '.join(missing_columns)}")

            # Check for unexpected columns (warn but don't fail)
            extra_columns = normalized_fields - all_columns
            if extra_columns:
                errors.append(f"Warning: Unexpected columns will be ignored: {', '.join(extra_columns)}")

            # Check if file has data
            rows = list(reader)
            if not rows:
                errors.append("CSV file has no data rows")

    except FileNotFoundError:
        errors.append(f"File not found: {file_path}")
    except PermissionError:
        errors.append(f"Permission denied: {file_path}")
    except Exception as e:
        errors.append(f"Error reading CSV file: {str(e)}")

    return len(errors) == 0, errors


def parse_csv_file(file_path: str) -> Tuple[List[AssociateRow], List[str]]:
    """
    Parse CSV file into AssociateRow objects.

    Args:
        file_path: Path to CSV file

    Returns:
        Tuple of (list of AssociateRow objects, list of parse errors)
    """
    rows = []
    errors = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Normalize field names
            if reader.fieldnames:
                reader.fieldnames = [col.strip().lower() for col in reader.fieldnames]

            for i, row_dict in enumerate(reader, start=2):  # Start at 2 (1 for header)
                try:
                    # Extract and clean values
                    first_name = row_dict.get('first_name', '').strip()
                    last_name = row_dict.get('last_name', '').strip()
                    level = row_dict.get('level', '').strip()
                    manager_first = row_dict.get('manager_first_name', '').strip() or None
                    manager_last = row_dict.get('manager_last_name', '').strip() or None

                    # Parse is_people_manager (optional, defaults to False)
                    is_people_manager_str = row_dict.get('is_people_manager', '').strip().lower()
                    is_people_manager = is_people_manager_str in ('true', 'yes', '1', 'y')

                    # Validate required fields
                    if not first_name:
                        errors.append(f"Row {i}: first_name is required")
                        continue
                    if not last_name:
                        errors.append(f"Row {i}: last_name is required")
                        continue
                    if not level:
                        errors.append(f"Row {i}: level is required")
                        continue

                    # Validate manager fields (both or neither)
                    if (manager_first and not manager_last) or (manager_last and not manager_first):
                        errors.append(
                            f"Row {i}: Both manager_first_name and manager_last_name must be "
                            "provided together, or both left empty"
                        )
                        continue

                    rows.append(AssociateRow(
                        row_number=i,
                        first_name=first_name,
                        last_name=last_name,
                        level=level,
                        manager_first_name=manager_first,
                        manager_last_name=manager_last,
                        is_people_manager=is_people_manager
                    ))

                except Exception as e:
                    errors.append(f"Row {i}: Error parsing row - {str(e)}")

    except Exception as e:
        errors.append(f"Error reading CSV file: {str(e)}")

    return rows, errors


def import_associates_from_csv(
    db: Session,
    file_path: str,
    update_existing: bool = False
) -> ImportResult:
    """
    Import associates from CSV file.

    CSV Format:
    first_name,last_name,level,manager_first_name,manager_last_name,is_people_manager

    Note: is_people_manager is optional and defaults to False.
          Accepts: true/yes/1/y (case-insensitive) for True, anything else for False.
          If associates have direct reports, they will be automatically marked as people managers
          regardless of this field value.

    Args:
        db: Database session
        file_path: Path to CSV file
        update_existing: If True, update existing associates; if False, skip them

    Returns:
        ImportResult with details of the import operation
    """
    result = ImportResult(
        success=False,
        created_count=0,
        updated_count=0,
        skipped_count=0,
        errors=[],
        warnings=[]
    )

    # Validate file structure
    is_valid, validation_errors = validate_csv_file(file_path)
    if not is_valid:
        result.errors.extend(validation_errors)
        return result

    # Parse CSV file
    rows, parse_errors = parse_csv_file(file_path)
    if parse_errors:
        result.errors.extend(parse_errors)
        if not rows:  # If no valid rows, return early
            return result

    # Get all levels (cache for lookups)
    levels = db.execute(select(AssociateLevel)).scalars().all()
    level_map = {level.description.lower(): level for level in levels}

    # Get all existing associates (cache for lookups)
    existing_associates = db.execute(select(Associate)).scalars().all()
    associate_map = {
        (assoc.first_name.lower(), assoc.last_name.lower()): assoc
        for assoc in existing_associates
    }

    # Process all rows in a single transaction
    try:
        # Process each row - First pass: Create/update associates
        processed_associates = []

        for row in rows:
            try:
                # Find level
                level = level_map.get(row.level.lower())
                if not level:
                    result.errors.append(
                        f"Row {row.row_number}: Level '{row.level}' not found. "
                        f"Available levels: {', '.join(level_map.keys())}"
                    )
                    continue

                # Check if associate already exists
                associate_key = (row.first_name.lower(), row.last_name.lower())
                existing_associate = associate_map.get(associate_key)

                if existing_associate:
                    if update_existing:
                        # Update existing associate
                        existing_associate.associate_level_id = level.id
                        result.updated_count += 1
                        processed_associates.append(existing_associate)
                    else:
                        result.skipped_count += 1
                        result.warnings.append(
                            f"Row {row.row_number}: Associate '{row.first_name} {row.last_name}' "
                            "already exists (skipped)"
                        )
                    continue

                # Create new associate (manager will be assigned in second pass)
                new_associate = Associate(
                    first_name=row.first_name,
                    last_name=row.last_name,
                    associate_level_id=level.id,
                    is_people_manager=row.is_people_manager  # From CSV, will be set to True if they have direct reports
                )

                db.add(new_associate)
                processed_associates.append(new_associate)
                result.created_count += 1

                # Update cache
                associate_map[associate_key] = new_associate

            except Exception as e:
                result.errors.append(f"Row {row.row_number}: Error processing - {str(e)}")

        # Flush to get IDs for new associates
        db.flush()

        # Second pass: Assign managers
        for row in rows:
            try:
                # Find the associate we just created/updated
                associate_key = (row.first_name.lower(), row.last_name.lower())
                associate = associate_map.get(associate_key)

                if not associate:
                    continue  # Already reported error in first pass

                # Assign manager if specified
                if row.manager_first_name and row.manager_last_name:
                    manager_key = (row.manager_first_name.lower(), row.manager_last_name.lower())
                    manager = associate_map.get(manager_key)

                    if not manager:
                        result.warnings.append(
                            f"Row {row.row_number}: Manager '{row.manager_first_name} "
                            f"{row.manager_last_name}' not found for '{row.first_name} {row.last_name}'. "
                            "Ensure manager is defined earlier in the CSV or already exists in database."
                        )
                    else:
                        associate.manager_id = manager.id
                        # Mark manager as people manager
                        manager.is_people_manager = True

            except Exception as e:
                result.errors.append(
                    f"Row {row.row_number}: Error assigning manager - {str(e)}"
                )

        # Commit entire transaction
        db.commit()
        result.success = True
    except Exception as e:
        db.rollback()
        result.success = False
        result.errors.append(f"Database error: {str(e)}")

    return result


def generate_sample_csv(file_path: str) -> None:
    """
    Generate a sample CSV file with example data.

    Args:
        file_path: Path where sample CSV should be created
    """
    sample_data = [
        {
            'first_name': 'John',
            'last_name': 'CEO',
            'level': 'Executive',
            'manager_first_name': '',
            'manager_last_name': '',
            'is_people_manager': 'true'
        },
        {
            'first_name': 'Jane',
            'last_name': 'Director',
            'level': 'Director',
            'manager_first_name': 'John',
            'manager_last_name': 'CEO',
            'is_people_manager': 'true'
        },
        {
            'first_name': 'Bob',
            'last_name': 'Manager',
            'level': 'Manager',
            'manager_first_name': 'Jane',
            'manager_last_name': 'Director',
            'is_people_manager': 'true'
        },
        {
            'first_name': 'Alice',
            'last_name': 'Employee',
            'level': 'Individual Contributor',
            'manager_first_name': 'Bob',
            'manager_last_name': 'Manager',
            'is_people_manager': 'false'
        },
    ]

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['first_name', 'last_name', 'level', 'manager_first_name', 'manager_last_name', 'is_people_manager']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_data)
