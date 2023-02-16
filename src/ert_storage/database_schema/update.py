from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional, Sequence

from ert_storage.database import Base
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4, UUID

if TYPE_CHECKING:
    from .ensemble import Ensemble
    from .observation import ObservationTransformation


class Update(Base):
    __tablename__ = "update"
    __table_args__ = (
        sa.UniqueConstraint("ensemble_result_pk", name="uq_update_result_pk"),
    )

    pk: Mapped[int] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(unique=True, default=uuid4)
    algorithm: Mapped[str]
    ensemble_reference_pk: Mapped[Optional[int]] = mapped_column(
        sa.ForeignKey("ensemble.pk")
    )
    ensemble_result_pk: Mapped[Optional[int]] = mapped_column(
        sa.ForeignKey("ensemble.pk")
    )

    ensemble_reference: Mapped[Ensemble] = relationship(
        "Ensemble",
        foreign_keys=[ensemble_reference_pk],
        back_populates="children",
    )
    ensemble_result: Mapped[Ensemble] = relationship(
        "Ensemble",
        foreign_keys=[ensemble_result_pk],
        uselist=False,
        back_populates="parent",
    )
    observation_transformations: Mapped[List[ObservationTransformation]] = relationship(
        "ObservationTransformation",
        foreign_keys="[ObservationTransformation.update_pk]",
        cascade="all, delete-orphan",
    )
