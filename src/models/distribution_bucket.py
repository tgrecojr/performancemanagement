"""DistributionBucket model representing groupings of performance ratings for distribution management."""
from sqlalchemy import Integer, String, Float, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .performance_rating import PerformanceRating


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

    def __repr__(self) -> str:
        return f"<DistributionBucket(id={self.id}, name='{self.name}', range={self.min_percentage}-{self.max_percentage}%)>"
