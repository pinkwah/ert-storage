from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Sequence
from uuid import uuid4, UUID

import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ert_storage.ext.sqlalchemy_arrays import FloatArray
from ert_storage.database import Base

from ._userdata_field import UserdataField
from .observation import observation_record_association
from .record_info import RecordType, RecordClass

if TYPE_CHECKING:
    from .ensemble import Ensemble
    from .observation import Observation
    from .record_info import RecordInfo


class Record(UserdataField, Base):
    __tablename__ = "record"

    pk = sa.Column(sa.Integer, primary_key=True)
    id: Mapped[UUID] = mapped_column(unique=True, default=uuid4)
    time_created = sa.Column(sa.DateTime, server_default=func.now())
    time_updated = sa.Column(
        sa.DateTime, server_default=func.now(), onupdate=func.now()
    )

    realization_index: Mapped[Optional[int]]

    record_info_pk = sa.Column(
        sa.Integer, sa.ForeignKey("record_info.pk"), nullable=True
    )
    record_info: Mapped[RecordInfo] = relationship(
        "RecordInfo", back_populates="records"
    )

    file_pk = sa.Column(sa.Integer, sa.ForeignKey("file.pk"))
    f64_matrix_pk = sa.Column(sa.Integer, sa.ForeignKey("f64_matrix.pk"))

    file: Mapped[File] = relationship("File", cascade="all")
    f64_matrix: Mapped[F64Matrix] = relationship("F64Matrix", cascade="all")

    observations: Mapped[List[Observation]] = relationship(
        "Observation",
        secondary=observation_record_association,
        back_populates="records",
    )

    @property
    def data(self) -> Any:
        info = self.record_info
        if info.record_type == RecordType.file:
            return self.file.content
        elif info.record_type == RecordType.f64_matrix:
            return self.f64_matrix.content
        else:
            raise NotImplementedError(
                f"The record type {self.record_type} is not yet implemented"
            )

    @property
    def ensemble_pk(self) -> sa.Column[int]:
        return self.record_info.ensemble_pk

    @property
    def name(self) -> str:
        return self.record_info.name

    @property
    def record_type(self) -> RecordType:
        return self.record_info.record_type

    @property
    def record_class(self) -> RecordClass:
        return self.record_info.record_class

    @property
    def has_observations(self) -> bool:
        return len(self.observations) > 0


class File(Base):
    __tablename__ = "file"

    pk: Mapped[int] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(unique=True, default=uuid4)
    time_created = sa.Column(sa.DateTime, server_default=func.now())
    time_updated = sa.Column(
        sa.DateTime, server_default=func.now(), onupdate=func.now()
    )

    filename: Mapped[str]
    mimetype: Mapped[str]

    content: Mapped[bytes] = mapped_column(sa.LargeBinary)
    az_container = sa.Column(sa.String)
    az_blob = sa.Column(sa.String)


class F64Matrix(Base):
    __tablename__ = "f64_matrix"

    pk = sa.Column(sa.Integer, primary_key=True)
    id: Mapped[UUID] = mapped_column(unique=True, default=uuid4)
    time_created = sa.Column(sa.DateTime, server_default=func.now())
    time_updated = sa.Column(
        sa.DateTime, server_default=func.now(), onupdate=func.now()
    )
    content: Mapped[Sequence[Sequence[float]]] = mapped_column(FloatArray)
    labels: Mapped[Sequence[Sequence[str]]] = mapped_column(sa.PickleType)


class FileBlock(Base):
    __tablename__ = "file_block"

    pk: Mapped[int] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(unique=True, default=uuid4)
    time_created = sa.Column(sa.DateTime, server_default=func.now())
    time_updated = sa.Column(
        sa.DateTime, server_default=func.now(), onupdate=func.now()
    )
    block_id: Mapped[str]
    block_index: Mapped[int]
    record_name: Mapped[str]
    realization_index: Mapped[Optional[int]]
    ensemble_pk = sa.Column(sa.Integer, sa.ForeignKey("ensemble.pk"), nullable=True)
    ensemble: Mapped[Ensemble] = relationship("Ensemble")
    content: Mapped[bytes] = mapped_column(sa.LargeBinary(), nullable=True)
