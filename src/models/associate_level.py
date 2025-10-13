"""AssociateLevel model representing hierarchical positions in the company."""
from sqlalchemy import Integer, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .associate import Associate


class AssociateLevel(Base):
    """
    Represents an employee's hierarchical position in the company.

    Attributes:
        id: Primary key
        description: Description of the level (e.g., "Junior Developer", "Senior Manager")
        level_indicator: Numeric indicator where lower numbers represent lower hierarchy levels
    """
    __tablename__ = "associate_levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    level_indicator: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    # Relationships
    associates: Mapped[List["Associate"]] = relationship(
        "Associate",
        back_populates="associate_level",
        cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("level_indicator > 0", name="level_indicator_positive"),
    )

    def __repr__(self) -> str:
        return f"<AssociateLevel(id={self.id}, description='{self.description}', level={self.level_indicator})>"
