from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Sequence
import sqlalchemy as sa
from ert_storage.database import Base
from ert_storage.ext.sqlalchemy_arrays import StringArray, FloatArray
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableList
from uuid import uuid4, UUID
from ._userdata_field import UserdataField

if TYPE_CHECKING:
    from .experiment import Experiment
    from .record import Record
    from .update import Update

observation_record_association = sa.Table(
    "observation_record_association",
    Base.metadata,
    sa.Column("observation_pk", sa.Integer, sa.ForeignKey("observation.pk")),
    sa.Column("record_pk", sa.Integer, sa.ForeignKey("record.pk")),
)


class Observation(UserdataField, Base):
    __tablename__ = "observation"
    __table_args__ = (
        sa.UniqueConstraint("name", "experiment_pk", name="uq_observation_name"),
    )

    pk: Mapped[int] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(unique=True, default=uuid4, nullable=False)
    time_created: Mapped[datetime] = mapped_column(server_default=func.now())
    time_updated: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    name: Mapped[str]
    x_axis: Mapped[Sequence[str]] = mapped_column(sa.PickleType)
    values: Mapped[Sequence[float]] = mapped_column(sa.PickleType)
    errors: Mapped[Sequence[float]] = mapped_column(sa.PickleType)

    records: Mapped[List[Record]] = relationship(
        "Record",
        secondary=observation_record_association,
        back_populates="observations",
    )
    experiment_pk = sa.Column(
        sa.Integer, sa.ForeignKey("experiment.pk"), nullable=False
    )
    experiment: Mapped[Experiment] = relationship("Experiment")


class ObservationTransformation(Base):
    __tablename__ = "observation_transformation"

    pk: Mapped[int] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(unique=True, default=uuid4)
    active_list = sa.Column(sa.PickleType, nullable=False)
    scale_list = sa.Column(sa.PickleType, nullable=False)

    observation_pk = sa.Column(
        sa.Integer, sa.ForeignKey("observation.pk"), nullable=False
    )
    observation: Mapped[Observation] = relationship("Observation")

    update_pk = sa.Column(sa.Integer, sa.ForeignKey("update.pk"), nullable=False)
    update: Mapped[Update] = relationship(
        "Update", back_populates="observation_transformations"
    )
