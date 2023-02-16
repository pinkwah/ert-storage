from __future__ import annotations

from typing import TYPE_CHECKING, List, Sequence
from uuid import uuid4, UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from ert_storage.database import Base
from ert_storage.ext.sqlalchemy_arrays import StringArray, IntArray
from ._userdata_field import UserdataField

if TYPE_CHECKING:
    from .experiment import Experiment
    from .record_info import RecordInfo
    from .update import Update


class Ensemble(Base, UserdataField):
    __tablename__ = "ensemble"

    pk = sa.Column(sa.Integer, primary_key=True)
    id: Mapped[UUID] = mapped_column(unique=True, default=uuid4, nullable=False)
    size = sa.Column(sa.Integer, nullable=False)
    active_realizations: Mapped[List[int]] = mapped_column(sa.PickleType)
    time_created = sa.Column(sa.DateTime, server_default=func.now())
    time_updated = sa.Column(
        sa.DateTime, server_default=func.now(), onupdate=func.now()
    )
    parameter_names: Mapped[List[str]] = mapped_column(sa.PickleType)
    response_names: Mapped[List[str]] = mapped_column(sa.PickleType)
    record_infos: Mapped[List[RecordInfo]] = relationship(
        "RecordInfo",
        foreign_keys="[RecordInfo.ensemble_pk]",
        cascade="all, delete-orphan",
        lazy="dynamic",
        back_populates="ensemble",
    )
    experiment_pk = sa.Column(
        sa.Integer, sa.ForeignKey("experiment.pk"), nullable=False
    )
    experiment: Mapped[Experiment] = relationship(
        "Experiment", back_populates="ensembles"
    )
    children: Mapped[List[Update]] = relationship(
        "Update",
        foreign_keys="[Update.ensemble_reference_pk]",
    )
    parent: Mapped[Update] = relationship(
        "Update",
        uselist=False,
        foreign_keys="[Update.ensemble_result_pk]",
        cascade="all, delete-orphan",
    )

    @property
    def parent_ensemble_id(self) -> UUID:
        return self.parent.ensemble_reference.id

    @property
    def child_ensemble_ids(self) -> Sequence[UUID]:
        return [x.ensemble_result.id for x in self.children]

    @property
    def experiment_id(self) -> UUID:
        return self.experiment.id
