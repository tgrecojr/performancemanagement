"""Test script for CSV import functionality."""
from src.database import get_db, init_db
from src.utils.csv_importer import import_associates_from_csv, generate_sample_csv
from src.models import Associate, AssociateLevel
import os

def test_csv_import():
    """Test CSV import functionality."""
    print("Initializing database...")
    init_db()

    db = get_db()

    # Check existing levels
    print("Checking existing associate levels...")
    levels = db.query(AssociateLevel).order_by(AssociateLevel.level_indicator).all()
    if not levels:
        print("  No levels found. Please create levels first using the UI.")
        db.close()
        return

    print("  Found levels:")
    for level in levels:
        print(f"    - {level.description} (level {level.level_indicator})")
    print("Levels ready!")

    # Generate sample CSV
    sample_path = "test_associates.csv"
    print(f"\nGenerating sample CSV: {sample_path}")
    generate_sample_csv(sample_path)
    print(f"Sample CSV created!")

    # Import the CSV
    print(f"\nImporting associates from {sample_path}...")
    result = import_associates_from_csv(db, sample_path, update_existing=False)

    # Display results
    print("\n" + "="*60)
    print(f"Import {'SUCCESSFUL' if result.success else 'FAILED'}")
    print("="*60)
    print(f"Created: {result.created_count}")
    print(f"Updated: {result.updated_count}")
    print(f"Skipped: {result.skipped_count}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")

    # Verify the import
    print("\n" + "="*60)
    print("Verifying imported associates...")
    print("="*60)
    associates = db.query(Associate).all()
    for assoc in associates:
        manager_name = assoc.manager.full_name if assoc.manager else "(None)"
        print(f"  {assoc.full_name:20s} | Level: {assoc.associate_level.description:20s} | Manager: {manager_name}")

    db.close()

    print("\n✓ CSV import test completed!")
    print(f"\nYou can now use the sample file: {os.path.abspath(sample_path)}")

if __name__ == "__main__":
    test_csv_import()
