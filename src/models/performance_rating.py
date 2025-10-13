"""PerformanceRating model representing employee performance ratings."""
from sqlalchemy import Integer, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .associate import Associate


class PerformanceRating(Base):
    """
    Represents performance ratings that can be assigned to associates.

    Attributes:
        id: Primary key
        description: Description of the rating (e.g., "Exceeds Expectations", "Needs Improvement")
        level_indicator: Numeric indicator where lower numbers = lower performance, higher = better performance
    """
    __tablename__ = "performance_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    level_indicator: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    # Relationships
    associates: Mapped[List["Associate"]] = relationship(
        "Associate",
        back_populates="performance_rating"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("level_indicator > 0", name="performance_level_positive"),
    )

    def __repr__(self) -> str:
        return f"<PerformanceRating(id={self.id}, description='{self.description}', level={self.level_indicator})>"
