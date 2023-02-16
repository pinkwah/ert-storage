from __future__ import annotations
from datetime import datetime

from enum import Enum
from typing import TYPE_CHECKING, List

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ert_storage.database import Base

if TYPE_CHECKING:
    from .record import Record
    from .ensemble import Ensemble


class RecordType(Enum):
    f64_matrix = 1
    file = 2


class RecordClass(Enum):
    parameter = 1
    response = 2
    other = 3


class RecordInfo(Base):
    __tablename__ = "record_info"
    __table_args__ = (sa.UniqueConstraint("name", "ensemble_pk"),)

    pk: Mapped[int] = mapped_column(primary_key=True)
    time_created: Mapped[datetime] = mapped_column(server_default=func.now())
    time_updated: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    ensemble_pk = sa.Column(sa.Integer, sa.ForeignKey("ensemble.pk"), nullable=False)
    ensemble: Mapped[Ensemble] = relationship("Ensemble")

    records: Mapped[List[Record]] = relationship(
        "Record",
        foreign_keys="[Record.record_info_pk]",
        cascade="all, delete-orphan",
    )

    name: Mapped[str]
    record_type: Mapped[RecordType]
    record_class: Mapped[RecordClass]

    # Parameter-specific data
    prior_pk = sa.Column(sa.Integer, sa.ForeignKey("prior.pk"), nullable=True)
    prior = relationship("Prior")
