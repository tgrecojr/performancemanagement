"""PerformanceRating model representing employee performance ratings."""
from sqlalchemy import Integer, String, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .associate import Associate
    from .distribution_bucket import DistributionBucket


class PerformanceRating(Base):
    """
    Represents performance ratings that can be assigned to associates.

    Attributes:
        id: Primary key
        description: Description of the rating (e.g., "Exceeds Expectations", "Needs Improvement")
        level_indicator: Numeric indicator where lower numbers = lower performance, higher = better performance
        excluded_from_distribution: If True, associates with this rating are excluded from distribution calculations
        distribution_bucket_id: Foreign key to DistributionBucket (nullable)
    """
    __tablename__ = "performance_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    level_indicator: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    # New fields for distribution management
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

    def __repr__(self) -> str:
        return f"<PerformanceRating(id={self.id}, description='{self.description}', level={self.level_indicator})>"
