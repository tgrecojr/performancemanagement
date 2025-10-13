"""Data management utilities for bulk operations."""
from typing import Tuple
from sqlalchemy.orm import Session

from ..models import Associate


def clear_all_associates(db: Session) -> Tuple[bool, int, str]:
    """
    Delete all associates from the database.

    This is a destructive operation that removes all associate records.
    Use with caution!

    Args:
        db: Database session

    Returns:
        Tuple of (success, count_deleted, message)
    """
    try:
        # Get count before deletion
        count = db.query(Associate).count()

        if count == 0:
            return True, 0, "No associates to delete"

        # Delete all associates
        # Note: This will cascade due to the relationship definitions
        db.query(Associate).delete()
        db.commit()

        return True, count, f"Successfully deleted {count} associate(s)"

    except Exception as e:
        db.rollback()
        return False, 0, f"Error deleting associates: {str(e)}"
