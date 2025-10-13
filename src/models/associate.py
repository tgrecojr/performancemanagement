"""Associate model representing employees in the organization."""
from sqlalchemy import Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List

from .base import Base


class Associate(Base):
    """
    Represents an employee/associate in the organization.

    Supports a self-referencing hierarchical structure where associates can have managers
    who are also associates, enabling multi-level corporate reporting structures.

    Attributes:
        id: Primary key
        first_name: Associate's first name
        last_name: Associate's last name
        associate_level_id: Foreign key to AssociateLevel
        manager_id: Foreign key to another Associate (self-referencing for hierarchy)
        is_people_manager: Boolean indicating if this associate has direct reports
        performance_rating_id: Foreign key to PerformanceRating (nullable until assigned)
    """
    __tablename__ = "associates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Foreign Keys
    associate_level_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("associate_levels.id", ondelete="RESTRICT"),
        nullable=False
    )
    manager_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("associates.id", ondelete="SET NULL"),
        nullable=True
    )
    performance_rating_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("performance_ratings.id", ondelete="SET NULL"),
        nullable=True
    )

    is_people_manager: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    # Relationships
    associate_level: Mapped["AssociateLevel"] = relationship(
        "AssociateLevel",
        back_populates="associates"
    )

    performance_rating: Mapped[Optional["PerformanceRating"]] = relationship(
        "PerformanceRating",
        back_populates="associates"
    )

    # Self-referencing relationship for manager hierarchy
    manager: Mapped[Optional["Associate"]] = relationship(
        "Associate",
        remote_side=[id],
        back_populates="direct_reports",
        foreign_keys=[manager_id]
    )

    direct_reports: Mapped[List["Associate"]] = relationship(
        "Associate",
        back_populates="manager",
        foreign_keys=[manager_id],
        cascade="all"
    )

    @property
    def full_name(self) -> str:
        """Return the full name of the associate."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Associate(id={self.id}, name='{self.full_name}', is_manager={self.is_people_manager})>"
