from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, List
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4, UUID
from ert_storage.database import Base
from ert_storage.ext.sqlalchemy_arrays import StringArray, FloatArray
from ._userdata_field import UserdataField


if TYPE_CHECKING:
    from .experiment import Experiment


class PriorFunction(Enum):
    const = 1
    trig = 2
    normal = 3
    lognormal = 4
    ert_truncnormal = 5
    stdnormal = 6
    uniform = 7
    ert_duniform = 8
    loguniform = 9
    ert_erf = 10
    ert_derf = 11


class Prior(Base, UserdataField):
    __tablename__ = "prior"

    pk: Mapped[int] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(unique=True, default=uuid4)
    time_created = sa.Column(sa.DateTime, server_default=func.now())
    time_updated = sa.Column(
        sa.DateTime, server_default=func.now(), onupdate=func.now()
    )

    name: Mapped[str]
    function: Mapped[PriorFunction]
    argument_names: Mapped[List[str]] = mapped_column(sa.PickleType)
    argument_values: Mapped[List[float]] = mapped_column(sa.PickleType)

    experiment_pk: Mapped[int] = mapped_column(sa.ForeignKey("experiment.pk"))
    experiment: Mapped[Experiment] = relationship("Experiment")
