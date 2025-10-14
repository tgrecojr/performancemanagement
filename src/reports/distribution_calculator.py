"""
Distribution calculator for performance ratings.

This module provides functions to calculate performance rating distributions.
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func
from ..models import Associate, AssociateLevel, PerformanceRating, DistributionBucket


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


# New comprehensive distribution calculation system

@dataclass
class BucketDistribution:
    """Distribution information for a single bucket."""

    bucket_id: int
    bucket_name: str
    bucket_description: Optional[str]
    min_percentage: float
    max_percentage: float
    sort_order: int

    # Actual distribution
    count: int
    percentage: float

    # Ratings included in this bucket
    rating_breakdown: Dict[str, int]  # rating_description -> count

    # Status indicators
    is_below_minimum: bool
    is_above_maximum: bool
    is_within_target: bool


@dataclass
class DistributionResult:
    """Encapsulates distribution calculation results."""

    # Headcount breakdown
    total_associates: int
    top_level_manager_count: int
    excluded_rating_count: int
    included_in_distribution_count: int
    unrated_count: int

    # Individual rating distributions (included only)
    rating_counts: Dict[str, int]  # rating_description -> count
    rating_percentages: Dict[str, float]  # rating_description -> percentage

    # Excluded rating details (for visibility)
    excluded_rating_counts: Dict[str, int]  # rating_description -> count

    # Bucket distributions
    bucket_distributions: List[BucketDistribution]


def calculate_comprehensive_distribution(db: Session) -> DistributionResult:
    """
    Calculate comprehensive distribution including all exclusions and bucketing.

    This is the main entry point for distribution calculations.

    Args:
        db: Database session

    Returns:
        DistributionResult with complete distribution information
    """
    # Get all associates with their ratings (eager load to prevent N+1)
    all_associates = db.execute(
        select(Associate).options(joinedload(Associate.performance_rating))
    ).scalars().all()

    # Separate into categories
    top_level_managers = []
    excluded_associates = []
    included_associates = []
    unrated_associates = []

    for assoc in all_associates:
        if assoc.manager_id is None:
            # Top level manager
            top_level_managers.append(assoc)
        elif assoc.performance_rating_id is None:
            # No rating assigned
            unrated_associates.append(assoc)
        elif assoc.performance_rating.excluded_from_distribution:
            # Has rating but it's excluded from distribution
            excluded_associates.append(assoc)
        else:
            # Included in distribution
            included_associates.append(assoc)

    # Calculate counts
    total_count = len(all_associates)
    included_count = len(included_associates)

    # Calculate individual rating distributions (included only)
    rating_counts = {}
    for assoc in included_associates:
        rating_desc = assoc.performance_rating.description
        rating_counts[rating_desc] = rating_counts.get(rating_desc, 0) + 1

    rating_percentages = {}
    if included_count > 0:
        for rating, count in rating_counts.items():
            rating_percentages[rating] = (count / included_count) * 100

    # Calculate excluded rating counts (for visibility in reports)
    excluded_rating_counts = {}
    for assoc in excluded_associates:
        rating_desc = assoc.performance_rating.description
        excluded_rating_counts[rating_desc] = excluded_rating_counts.get(rating_desc, 0) + 1

    # Calculate bucket distributions
    bucket_distributions = calculate_bucket_distributions(db, included_associates, included_count)

    return DistributionResult(
        total_associates=total_count,
        top_level_manager_count=len(top_level_managers),
        excluded_rating_count=len(excluded_associates),
        included_in_distribution_count=included_count,
        unrated_count=len(unrated_associates),
        rating_counts=rating_counts,
        rating_percentages=rating_percentages,
        excluded_rating_counts=excluded_rating_counts,
        bucket_distributions=bucket_distributions
    )


def calculate_bucket_distributions(
    db: Session,
    included_associates: List[Associate],
    included_count: int
) -> List[BucketDistribution]:
    """
    Calculate distribution for each defined bucket.

    Args:
        db: Database session
        included_associates: Associates included in distribution calculations
        included_count: Total count of included associates

    Returns:
        List of BucketDistribution objects, sorted by sort_order
    """
    # Get all buckets
    buckets = db.execute(
        select(DistributionBucket).order_by(DistributionBucket.sort_order)
    ).scalars().all()

    bucket_results = []

    for bucket in buckets:
        # Count associates in this bucket
        bucket_count = 0
        rating_breakdown = {}

        for assoc in included_associates:
            if assoc.performance_rating.distribution_bucket_id == bucket.id:
                bucket_count += 1
                rating_desc = assoc.performance_rating.description
                rating_breakdown[rating_desc] = rating_breakdown.get(rating_desc, 0) + 1

        # Calculate percentage
        percentage = (bucket_count / included_count * 100) if included_count > 0 else 0.0

        # Determine status
        is_below_minimum = percentage < bucket.min_percentage
        is_above_maximum = percentage > bucket.max_percentage
        is_within_target = not (is_below_minimum or is_above_maximum)

        bucket_results.append(BucketDistribution(
            bucket_id=bucket.id,
            bucket_name=bucket.name,
            bucket_description=bucket.description,
            min_percentage=bucket.min_percentage,
            max_percentage=bucket.max_percentage,
            sort_order=bucket.sort_order,
            count=bucket_count,
            percentage=percentage,
            rating_breakdown=rating_breakdown,
            is_below_minimum=is_below_minimum,
            is_above_maximum=is_above_maximum,
            is_within_target=is_within_target
        ))

    return bucket_results


def get_unassigned_ratings(db: Session) -> List[PerformanceRating]:
    """
    Get performance ratings that are not assigned to any distribution bucket.

    This is useful for validation and configuration screens to identify
    ratings that need bucket assignment.

    Args:
        db: Database session

    Returns:
        List of PerformanceRating objects with no bucket assignment
    """
    query = select(PerformanceRating).where(
        PerformanceRating.distribution_bucket_id.is_(None),
        PerformanceRating.excluded_from_distribution.is_(False)
    )
    return list(db.execute(query).scalars().all())


def validate_bucket_configuration(db: Session) -> Dict[str, List[str]]:
    """
    Validate the distribution bucket configuration for common issues.

    Returns a dictionary of validation errors/warnings by category.

    Args:
        db: Database session

    Returns:
        Dict with keys: 'errors', 'warnings', each containing list of messages
    """
    errors = []
    warnings = []

    # Check if there are unassigned ratings
    unassigned = get_unassigned_ratings(db)
    if unassigned:
        rating_names = [r.description for r in unassigned]
        warnings.append(
            f"The following ratings are not assigned to any distribution bucket: "
            f"{', '.join(rating_names)}"
        )

    # Check if min/max percentages across all buckets make sense
    buckets = db.execute(select(DistributionBucket)).scalars().all()

    if buckets:
        total_min = sum(b.min_percentage for b in buckets)
        total_max = sum(b.max_percentage for b in buckets)

        if total_min > 100:
            errors.append(
                f"Sum of minimum percentages ({total_min:.1f}%) exceeds 100%. "
                "This configuration is impossible to achieve."
            )

        if total_max < 100:
            errors.append(
                f"Sum of maximum percentages ({total_max:.1f}%) is less than 100%. "
                "This configuration is impossible to achieve."
            )

        # Check for overlapping issues
        if total_min < 100 < total_max:
            # This is the ideal case - there's room to maneuver
            pass
        elif total_min == 100 and total_max == 100:
            warnings.append(
                "Distribution targets are very rigid (sum of mins = sum of maxs = 100%). "
                "There is no flexibility in the distribution."
            )

    return {
        'errors': errors,
        'warnings': warnings
    }


# Manager Distribution Analysis


@dataclass
class ManagerDistributionDetail:
    """Distribution details for a single manager."""

    manager_id: int
    manager_name: str
    manager_level: str
    hierarchy_level: int  # Distance from top (0 = top level, 1 = reports to top, etc.)

    # Headcount breakdown
    total_direct_reports: int
    rated_reports: int
    unrated_reports: int
    excluded_reports: int
    included_reports: int  # Those included in distribution calculations

    # Rating distributions (for included reports only)
    rating_counts: Dict[str, int]  # rating_description -> count
    rating_percentages: Dict[str, float]  # rating_description -> percentage

    # Bucket distributions (for included reports only)
    bucket_counts: Dict[str, int]  # bucket_name -> count
    bucket_percentages: Dict[str, float]  # bucket_name -> percentage

    # Status indicators for buckets
    buckets_out_of_range: List[str]  # List of bucket names that are out of target range


@dataclass
class ManagerDistributionReport:
    """Complete manager distribution report."""

    # Overall summary across all managers
    total_managers: int
    total_associates_under_managers: int

    # Individual manager details
    manager_details: List[ManagerDistributionDetail]

    # Hierarchy level summaries
    hierarchy_summaries: Dict[int, Dict]  # hierarchy_level -> summary dict


def calculate_hierarchy_level(db: Session, associate: Associate) -> int:
    """
    Calculate the hierarchy level of an associate (distance from top).

    0 = Top level (no manager)
    1 = Reports directly to top level
    2 = Reports to someone who reports to top level
    etc.

    Args:
        db: Database session
        associate: Associate to calculate level for

    Returns:
        Hierarchy level (0 = top)
    """
    level = 0
    current = associate

    # Prevent infinite loops in case of circular references
    seen_ids = set()

    while current.manager_id is not None:
        if current.manager_id in seen_ids:
            # Circular reference detected
            break
        seen_ids.add(current.id)

        # Get the manager
        current = db.execute(
            select(Associate).where(Associate.id == current.manager_id)
        ).scalar_one()
        level += 1

    return level


def calculate_manager_distributions(db: Session) -> ManagerDistributionReport:
    """
    Calculate performance rating distributions across all managers.

    This provides two views:
    1. Overall: Distribution for each individual manager
    2. By Hierarchy Level: Aggregated distributions at each level of the org chart

    Args:
        db: Database session

    Returns:
        ManagerDistributionReport with comprehensive manager distribution data
    """
    # Get all associates who are people managers
    managers = db.execute(
        select(Associate)
        .where(Associate.is_people_manager.is_(True))
        .options(joinedload(Associate.direct_reports))
    ).unique().scalars().all()

    # Get all buckets for reference
    buckets = db.execute(
        select(DistributionBucket).order_by(DistributionBucket.sort_order)
    ).scalars().all()
    bucket_map = {b.id: b for b in buckets}

    manager_details = []
    hierarchy_data = {}  # hierarchy_level -> list of ManagerDistributionDetail

    for manager in managers:
        # Calculate manager's hierarchy level
        hierarchy_level = calculate_hierarchy_level(db, manager)

        # Categorize direct reports
        total_reports = len(manager.direct_reports)
        rated_reports = []
        unrated_reports = []
        excluded_reports = []
        included_reports = []

        for report in manager.direct_reports:
            if report.performance_rating_id is None:
                unrated_reports.append(report)
            elif report.performance_rating.excluded_from_distribution:
                excluded_reports.append(report)
            else:
                rated_reports.append(report)
                included_reports.append(report)

        # Calculate rating distributions (included only)
        rating_counts = {}
        for report in included_reports:
            rating_desc = report.performance_rating.description
            rating_counts[rating_desc] = rating_counts.get(rating_desc, 0) + 1

        rating_percentages = {}
        if included_reports:
            for rating, count in rating_counts.items():
                rating_percentages[rating] = (count / len(included_reports)) * 100

        # Calculate bucket distributions (included only)
        bucket_counts = {}
        for report in included_reports:
            bucket_id = report.performance_rating.distribution_bucket_id
            if bucket_id and bucket_id in bucket_map:
                bucket_name = bucket_map[bucket_id].name
                bucket_counts[bucket_name] = bucket_counts.get(bucket_name, 0) + 1

        bucket_percentages = {}
        buckets_out_of_range = []
        if included_reports:
            for bucket in buckets:
                count = bucket_counts.get(bucket.name, 0)
                percentage = (count / len(included_reports)) * 100
                bucket_percentages[bucket.name] = percentage

                # Check if out of range
                if percentage < bucket.min_percentage or percentage > bucket.max_percentage:
                    if count > 0:  # Only flag if there are actually people in this bucket
                        buckets_out_of_range.append(bucket.name)

        detail = ManagerDistributionDetail(
            manager_id=manager.id,
            manager_name=manager.full_name,
            manager_level=manager.associate_level.description,
            hierarchy_level=hierarchy_level,
            total_direct_reports=total_reports,
            rated_reports=len(rated_reports),
            unrated_reports=len(unrated_reports),
            excluded_reports=len(excluded_reports),
            included_reports=len(included_reports),
            rating_counts=rating_counts,
            rating_percentages=rating_percentages,
            bucket_counts=bucket_counts,
            bucket_percentages=bucket_percentages,
            buckets_out_of_range=buckets_out_of_range
        )

        manager_details.append(detail)

        # Add to hierarchy data
        if hierarchy_level not in hierarchy_data:
            hierarchy_data[hierarchy_level] = []
        hierarchy_data[hierarchy_level].append(detail)

    # Calculate hierarchy level summaries
    hierarchy_summaries = {}
    for level, details in hierarchy_data.items():
        # Aggregate across all managers at this level
        total_managers_at_level = len(details)
        total_included = sum(d.included_reports for d in details)

        # Aggregate rating counts
        agg_rating_counts = {}
        for detail in details:
            for rating, count in detail.rating_counts.items():
                agg_rating_counts[rating] = agg_rating_counts.get(rating, 0) + count

        # Calculate aggregate percentages
        agg_rating_percentages = {}
        if total_included > 0:
            for rating, count in agg_rating_counts.items():
                agg_rating_percentages[rating] = (count / total_included) * 100

        # Aggregate bucket counts
        agg_bucket_counts = {}
        for detail in details:
            for bucket, count in detail.bucket_counts.items():
                agg_bucket_counts[bucket] = agg_bucket_counts.get(bucket, 0) + count

        # Calculate aggregate bucket percentages
        agg_bucket_percentages = {}
        if total_included > 0:
            for bucket, count in agg_bucket_counts.items():
                agg_bucket_percentages[bucket] = (count / total_included) * 100

        hierarchy_summaries[level] = {
            'hierarchy_level': level,
            'manager_count': total_managers_at_level,
            'total_included_reports': total_included,
            'rating_counts': agg_rating_counts,
            'rating_percentages': agg_rating_percentages,
            'bucket_counts': agg_bucket_counts,
            'bucket_percentages': agg_bucket_percentages
        }

    # Calculate overall totals
    total_associates_under_managers = sum(d.total_direct_reports for d in manager_details)

    return ManagerDistributionReport(
        total_managers=len(manager_details),
        total_associates_under_managers=total_associates_under_managers,
        manager_details=manager_details,
        hierarchy_summaries=hierarchy_summaries
    )
