# Performance Distribution System Implementation Proposal

## Overview

This document proposes a flexible, configurable implementation for handling distribution calculations with exclusions, groupings, and min/max targets. The design avoids hardcoding and allows for complete configurability through the UI.

## Core Design Principles

1. **No Hardcoding**: All distribution rules, exclusions, and groupings are data-driven
2. **Configurability**: All settings manageable through UI configuration screens
3. **Flexibility**: System adapts to changing business rules without code changes
4. **Transparency**: Reports clearly show what is included/excluded and why

---

## Data Model Changes

### 1. New Model: DistributionBucket

A distribution bucket represents a grouping of one or more performance ratings that are managed together against min/max distribution targets.

```python
class DistributionBucket(Base):
    """
    Represents a grouping of performance ratings for distribution management.

    Multiple performance ratings can be grouped into a single bucket that is
    managed to a minimum and maximum percentage target.

    Examples:
    - Bucket: "High Performers" (Very Strong + Exceptional): Min 15%, Max 25%
    - Bucket: "Core Performers" (Meets Expectations): Min 50%, Max 70%
    - Bucket: "Development Needed" (Below Expectations): Min 5%, Max 15%

    Attributes:
        id: Primary key
        name: Name of the distribution bucket (e.g., "High Performers")
        description: Optional longer description of what this bucket represents
        min_percentage: Minimum allowed percentage for this bucket (0-100)
        max_percentage: Maximum allowed percentage for this bucket (0-100)
        sort_order: Display order for reports (lower numbers first)
    """
    __tablename__ = "distribution_buckets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    min_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    max_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    performance_ratings: Mapped[List["PerformanceRating"]] = relationship(
        "PerformanceRating",
        back_populates="distribution_bucket"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("min_percentage >= 0 AND min_percentage <= 100",
                       name="min_percentage_valid"),
        CheckConstraint("max_percentage >= 0 AND max_percentage <= 100",
                       name="max_percentage_valid"),
        CheckConstraint("min_percentage <= max_percentage",
                       name="min_less_than_max"),
    )
```

### 2. Modified Model: PerformanceRating

Add new fields to track distribution behavior:

```python
class PerformanceRating(Base):
    """
    Represents performance ratings that can be assigned to associates.

    NEW FIELDS:
    - excluded_from_distribution: If True, associates with this rating are
      removed from the total headcount when calculating distribution percentages
    - distribution_bucket_id: Links this rating to a distribution bucket for
      min/max percentage management

    Attributes:
        id: Primary key
        description: Description of the rating
        level_indicator: Numeric indicator (lower = worse, higher = better)
        excluded_from_distribution: If True, excluded from distribution calcs
        distribution_bucket_id: Foreign key to DistributionBucket (nullable)
    """
    __tablename__ = "performance_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    level_indicator: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    # NEW FIELDS
    excluded_from_distribution: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    distribution_bucket_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("distribution_buckets.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    associates: Mapped[List["Associate"]] = relationship(
        "Associate",
        back_populates="performance_rating"
    )

    distribution_bucket: Mapped[Optional["DistributionBucket"]] = relationship(
        "DistributionBucket",
        back_populates="performance_ratings"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("level_indicator > 0", name="performance_level_positive"),
    )
```

---

## Distribution Calculation Logic

### Calculation Flow

```
1. Get all associates from database
2. Exclude top-level manager (manager_id IS NULL)
3. Separate associates by rating exclusion status:
   - Excluded: Associates with rating.excluded_from_distribution = True
   - Included: All others with ratings assigned
4. Calculate total headcount (included only)
5. Calculate individual rating distributions
6. Calculate bucket distributions (sum of ratings in each bucket)
7. Compare bucket percentages against min/max targets
8. Return comprehensive distribution report
```

### New Distribution Calculator Module

Update `src/reports/distribution_calculator.py` with new functions:

```python
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..models import Associate, PerformanceRating, DistributionBucket


@dataclass
class DistributionResult:
    """Encapsulates distribution calculation results."""

    # Headcount breakdown
    total_associates: int
    top_level_manager_count: int
    excluded_rating_count: int
    included_in_distribution_count: int
    unrated_count: int

    # Individual rating distributions
    rating_counts: Dict[str, int]  # rating_description -> count
    rating_percentages: Dict[str, float]  # rating_description -> percentage

    # Excluded rating details (for visibility)
    excluded_rating_counts: Dict[str, int]  # rating_description -> count

    # Bucket distributions
    bucket_distributions: List['BucketDistribution']


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


def calculate_comprehensive_distribution(db: Session) -> DistributionResult:
    """
    Calculate comprehensive distribution including all exclusions and bucketing.

    This is the main entry point for distribution calculations.

    Args:
        db: Database session

    Returns:
        DistributionResult with complete distribution information
    """
    # Get all associates with their ratings
    all_associates = db.execute(
        select(Associate)
        .join(Associate.performance_rating, isouter=True)
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
        PerformanceRating.excluded_from_distribution == False
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
```

---

## UI Changes

### 1. New Configuration Screen: Distribution Buckets

**Location**: `src/ui/distribution_buckets_screen.py`

**Features**:
- List all distribution buckets in a table
- Columns: Name, Description, Min%, Max%, Sort Order, Ratings Count
- CRUD operations:
  - Create new bucket
  - Edit existing bucket
  - Delete bucket (only if no ratings assigned)
  - View ratings assigned to bucket
- Validation:
  - Min % must be >= 0 and <= 100
  - Max % must be >= 0 and <= 100
  - Min % must be <= Max %
  - Show warnings from `validate_bucket_configuration()`

### 2. Enhanced Configuration Screen: Performance Ratings

**Update**: `src/ui/performance_ratings_screen.py`

**New Features**:
- Add column: "Excluded from Distribution" (checkbox/boolean)
- Add column: "Distribution Bucket" (dropdown selector)
- Allow editing these fields inline or in edit form
- Show warning icon if rating is not assigned to bucket and not excluded
- Filter view options:
  - Show all ratings
  - Show only included ratings
  - Show only excluded ratings
  - Show unassigned ratings (not in any bucket)

### 3. Enhanced Report Screen: Distribution Report

**Update**: `src/ui/distribution_report_screen.py`

**New Layout** (multiple tables/sections):

#### Section 1: Headcount Summary
```
┌─────────────────────────────────────────────────────┐
│ Headcount Summary                                   │
├─────────────────────────────────────────┬───────────┤
│ Total Associates                        │     147   │
│ Top-Level Manager (excluded)            │       1   │
│ Excluded Ratings (e.g., "Too New")     │      12   │
│ Unrated Associates                      │       8   │
│ ─────────────────────────────────────────────────── │
│ Included in Distribution                │     126   │
└─────────────────────────────────────────┴───────────┘
```

#### Section 2: Distribution Bucket Analysis
```
┌────────────────────────────────────────────────────────────────────────────┐
│ Distribution Bucket Analysis                                               │
├─────────────────┬───────┬─────────┬──────────┬────────┬────────┬──────────┤
│ Bucket          │ Count │ Actual% │ Min %    │ Max %  │ Status │ Ratings  │
├─────────────────┼───────┼─────────┼──────────┼────────┼────────┼──────────┤
│ High Performers │  25   │  19.8%  │  15.0%   │ 25.0%  │   ✓    │ ES, VS   │
│ Core Performers │  89   │  70.6%  │  60.0%   │ 75.0%  │   ✓    │ ME       │
│ Development     │  12   │   9.5%  │   5.0%   │ 15.0%  │   ✓    │ NI       │
└─────────────────┴───────┴─────────┴──────────┴────────┴────────┴──────────┘

Status Indicators:
  ✓ Within target range
  ↓ Below minimum (red/warning)
  ↑ Above maximum (red/warning)
```

#### Section 3: Individual Rating Distribution (Included)
```
┌──────────────────────────────────────────────────────────┐
│ Performance Rating Distribution (Included in Calc)       │
├────────────────────────────────┬───────┬─────────────────┤
│ Rating                         │ Count │ Percentage      │
├────────────────────────────────┼───────┼─────────────────┤
│ Exceptional                    │   8   │   6.3%          │
│ Very Strong                    │  17   │  13.5%          │
│ Meets Expectations             │  89   │  70.6%          │
│ Needs Improvement              │  12   │   9.5%          │
├────────────────────────────────┼───────┼─────────────────┤
│ Total                          │ 126   │ 100.0%          │
└────────────────────────────────┴───────┴─────────────────┘
```

#### Section 4: Excluded Associates (For Visibility)
```
┌──────────────────────────────────────────────────────────┐
│ Excluded from Distribution (For Visibility Only)         │
├────────────────────────────────┬─────────────────────────┤
│ Category                       │ Count                   │
├────────────────────────────────┼─────────────────────────┤
│ Top-Level Manager              │   1                     │
│ Too New to Rate                │  12                     │
│ Unrated                        │   8                     │
└────────────────────────────────┴─────────────────────────┘
```

#### Section 5: Distribution by Level (Existing, Enhanced)
```
┌────────────────────────────────────────────────────────────────────┐
│ Distribution by Associate Level                                    │
├────────────┬──────────┬────────────────────────────────────────────┤
│ Level      │ Total    │ Rating Distribution                        │
├────────────┼──────────┼────────────────────────────────────────────┤
│ Director   │  15      │ ES:3(20%), VS:5(33%), ME:6(40%), NI:1(7%) │
│ Manager    │  45      │ ES:2(4%), VS:8(18%), ME:32(71%), NI:3(7%) │
│ Individual │  66      │ ES:3(5%), VS:4(6%), ME:51(77%), NI:8(12%) │
└────────────┴──────────┴────────────────────────────────────────────┘
```

### 4. Main Menu Updates

**Update**: `src/ui/main_app.py`

Add new menu item under Configuration:
- "Distribution Buckets" → navigate to DistributionBucketsScreen

---

## Database Migration Strategy

### Migration File: `002_add_distribution_buckets.py`

```python
"""Add distribution buckets and rating exclusion support

Revision ID: 002
Revises: 001
Create Date: [timestamp]
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # Create distribution_buckets table
    op.create_table(
        'distribution_buckets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('min_percentage', sa.Float(), nullable=False),
        sa.Column('max_percentage', sa.Float(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.CheckConstraint('min_percentage >= 0 AND min_percentage <= 100',
                          name='min_percentage_valid'),
        sa.CheckConstraint('max_percentage >= 0 AND max_percentage <= 100',
                          name='max_percentage_valid'),
        sa.CheckConstraint('min_percentage <= max_percentage',
                          name='min_less_than_max'),
    )

    # Add new columns to performance_ratings
    op.add_column('performance_ratings',
                  sa.Column('excluded_from_distribution', sa.Boolean(),
                           nullable=False, server_default='0'))

    op.add_column('performance_ratings',
                  sa.Column('distribution_bucket_id', sa.Integer(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_performance_rating_distribution_bucket',
        'performance_ratings', 'distribution_buckets',
        ['distribution_bucket_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # Remove foreign key
    op.drop_constraint('fk_performance_rating_distribution_bucket',
                      'performance_ratings', type_='foreignkey')

    # Remove columns from performance_ratings
    op.drop_column('performance_ratings', 'distribution_bucket_id')
    op.drop_column('performance_ratings', 'excluded_from_distribution')

    # Drop distribution_buckets table
    op.drop_table('distribution_buckets')
```

---

## Implementation Phases

### Phase 1: Data Model & Migration
1. Create `DistributionBucket` model
2. Update `PerformanceRating` model with new fields
3. Create and test database migration
4. Update model `__init__.py` to export new model

### Phase 2: Business Logic
1. Implement new distribution calculation functions
2. Add dataclasses for results
3. Add validation functions
4. Write comprehensive unit tests

### Phase 3: UI - Configuration Screens
1. Create `DistributionBucketsScreen` (CRUD for buckets)
2. Update `PerformanceRatingsScreen` (add new fields)
3. Add validation and warning displays
4. Update main menu navigation

### Phase 4: UI - Reporting
1. Update `DistributionReportScreen` with new layout
2. Add multiple report sections
3. Add status indicators and color coding
4. Test with various data scenarios

### Phase 5: Testing & Documentation
1. End-to-end testing with realistic data
2. Edge case testing (empty buckets, no assignments, etc.)
3. Update user documentation
4. Create example configurations

---

## Example Configuration

Here's how a typical corporate distribution might be configured:

### Distribution Buckets

| Name | Description | Min % | Max % | Sort Order |
|------|-------------|-------|-------|------------|
| Top Performers | Exceptional and Very Strong performers | 15.0 | 25.0 | 1 |
| Solid Contributors | Meets expectations consistently | 60.0 | 75.0 | 2 |
| Needs Development | Below expectations, needs improvement | 5.0 | 15.0 | 3 |

### Performance Ratings

| Rating | Level | Excluded? | Bucket |
|--------|-------|-----------|--------|
| Exceptional | 5 | No | Top Performers |
| Very Strong | 4 | No | Top Performers |
| Meets Expectations | 3 | No | Solid Contributors |
| Needs Improvement | 2 | No | Needs Development |
| Unsatisfactory | 1 | No | Needs Development |
| Too New to Rate | 0 | Yes | (none) |
| On Leave | 0 | Yes | (none) |

### Calculation Example

Total Associates: 150
- Top-level manager: 1 (excluded)
- "Too New to Rate": 10 (excluded)
- "On Leave": 2 (excluded)
- Unrated: 7 (excluded)
- **Included in distribution: 130**

Distribution:
- Exceptional: 8 (6.2%)
- Very Strong: 18 (13.8%)
- **Top Performers bucket: 26 (20.0%)** ✓ [Target: 15-25%]

- Meets Expectations: 92 (70.8%)
- **Solid Contributors bucket: 92 (70.8%)** ✓ [Target: 60-75%]

- Needs Improvement: 10 (7.7%)
- Unsatisfactory: 2 (1.5%)
- **Needs Development bucket: 12 (9.2%)** ✓ [Target: 5-15%]

All buckets within target! ✓

---

## Benefits of This Approach

1. **Fully Configurable**: No hardcoded values, levels, or bucket names
2. **Flexible**: Easy to add new buckets, ratings, or change targets
3. **Transparent**: Clear visibility into what is included/excluded and why
4. **Maintainable**: Business rule changes require no code changes
5. **Validated**: Built-in validation prevents impossible configurations
6. **Auditable**: Reports clearly show all calculations and exclusions
7. **User-Friendly**: All configuration through UI screens

---

## Questions or Concerns?

Please review this proposal and let me know if:
1. Any requirements are misunderstood or missing
2. Any design decisions should be reconsidered
3. Any additional features or validations are needed
4. You're ready to proceed with implementation
