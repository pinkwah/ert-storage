import sqlalchemy as sa
from sqlalchemy.orm import Mapped, declarative_mixin, declared_attr, mapped_column


@declarative_mixin
class UserdataField:
    @declared_attr
    def userdata(cls) -> Mapped[sa.JSON]:
        return mapped_column(sa.JSON, nullable=False, default=dict)
