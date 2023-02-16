from __future__ import annotations

import sqlalchemy as sa
from uuid import uuid4, UUID
from typing import List, TYPE_CHECKING, Sequence
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ert_storage.database import Base
from ._userdata_field import UserdataField


if TYPE_CHECKING:
    from .ensemble import Ensemble
    from .observation import Observation
    from .prior import Prior


class Experiment(UserdataField, Base):
    __tablename__ = "experiment"

    pk = sa.Column(sa.Integer, primary_key=True)
    id: Mapped[UUID] = mapped_column(unique=True, default=uuid4, nullable=False)
    time_created = sa.Column(sa.DateTime, server_default=func.now())
    time_updated = sa.Column(
        sa.DateTime, server_default=func.now(), onupdate=func.now()
    )
    name = sa.Column(sa.String)
    ensembles: Mapped[List[Ensemble]] = relationship(
        "Ensemble",
        foreign_keys="[Ensemble.experiment_pk]",
        cascade="all, delete-orphan",
    )
    observations: Mapped[List[Observation]] = relationship(
        "Observation",
        foreign_keys="[Observation.experiment_pk]",
        cascade="all, delete-orphan",
        back_populates="experiment",
    )
    priors: Mapped[List[Prior]] = relationship(
        "Prior",
        foreign_keys="[Prior.experiment_pk]",
        cascade="all, delete-orphan",
        back_populates="experiment",
    )

    @property
    def ensemble_ids(self) -> List[UUID]:
        return [ens.id for ens in self.ensembles]
