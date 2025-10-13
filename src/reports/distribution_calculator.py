"""
Distribution calculator for performance ratings.

This module provides functions to calculate performance rating distributions.
"""
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..models import Associate, AssociateLevel, PerformanceRating


def get_total_headcount(db: Session) -> int:
    """
    Get the total headcount of associates with assigned ratings.

    Args:
        db: Database session

    Returns:
        Total number of associates with performance ratings
    """
    query = select(func.count(Associate.id)).where(
        Associate.performance_rating_id.isnot(None)
    )

    result = db.execute(query).scalar()
    return result or 0


def get_associates_by_rating(db: Session) -> Dict[str, int]:
    """
    Get count of associates by performance rating description.

    Args:
        db: Database session

    Returns:
        Dictionary mapping rating description to count
    """
    query = (
        select(
            PerformanceRating.description,
            func.count(Associate.id).label('count')
        )
        .join(
            Associate,
            PerformanceRating.id == Associate.performance_rating_id
        )
        .group_by(PerformanceRating.description)
    )

    result = db.execute(query).all()
    return {row.description: row.count for row in result}


def get_associates_by_level_and_rating(db: Session) -> Dict[Tuple[str, str], int]:
    """
    Get count of associates by level and rating.

    Args:
        db: Database session

    Returns:
        Dictionary mapping (level_description, rating_description) to count
    """
    query = (
        select(
            AssociateLevel.description.label('level_desc'),
            PerformanceRating.description.label('rating_desc'),
            func.count(Associate.id).label('count')
        )
        .join(
            AssociateLevel,
            Associate.associate_level_id == AssociateLevel.id
        )
        .join(
            PerformanceRating,
            Associate.performance_rating_id == PerformanceRating.id
        )
        .group_by(AssociateLevel.description, PerformanceRating.description)
    )

    result = db.execute(query).all()
    return {(row.level_desc, row.rating_desc): row.count for row in result}


def calculate_rating_distribution_percentages(db: Session) -> Dict[str, float]:
    """
    Calculate percentage distribution of performance ratings.

    Args:
        db: Database session

    Returns:
        Dictionary mapping rating description to percentage (0-100)
    """
    total = get_total_headcount(db)
    if total == 0:
        return {}

    counts = get_associates_by_rating(db)
    return {
        rating: (count / total) * 100
        for rating, count in counts.items()
    }


def get_unrated_associates(db: Session) -> List[Associate]:
    """
    Get all associates who do not have a performance rating assigned.

    Args:
        db: Database session

    Returns:
        List of Associate objects without performance ratings
    """
    query = select(Associate).where(Associate.performance_rating_id.is_(None))

    result = db.execute(query).scalars().all()
    return list(result)


def get_level_distribution_summary(db: Session) -> Dict[str, Dict]:
    """
    Get a comprehensive summary of distribution by level.

    For each level, returns:
    - Total associates at that level
    - Count by rating
    - Percentage distribution

    Returns:
        Dictionary mapping level description to summary dict
    """
    levels = db.execute(select(AssociateLevel)).scalars().all()
    summary = {}

    for level in levels:
        level_associates = (
            db.execute(
                select(Associate)
                .where(Associate.associate_level_id == level.id)
            )
            .scalars()
            .all()
        )

        total_at_level = len(level_associates)

        # Count by rating
        rating_counts = {}
        unrated_count = 0

        for assoc in level_associates:
            if assoc.performance_rating:
                rating_desc = assoc.performance_rating.description
                rating_counts[rating_desc] = rating_counts.get(rating_desc, 0) + 1
            else:
                unrated_count += 1

        # Calculate percentages
        rating_percentages = {}
        if total_at_level > 0:
            for rating, count in rating_counts.items():
                rating_percentages[rating] = (count / total_at_level) * 100

        summary[level.description] = {
            'level_indicator': level.level_indicator,
            'total_associates': total_at_level,
            'rated_associates': total_at_level - unrated_count,
            'unrated_associates': unrated_count,
            'rating_counts': rating_counts,
            'rating_percentages': rating_percentages,
        }

    return summary
