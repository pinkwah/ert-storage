"""
This module adds the FloatArray, StringArray and IntArray column types. In Postgresql,
both are native `sqlalchemy.ARRAY`s, while on SQLite, they are `PickleType`s.

In order to have graphene_sqlalchemy dump the arrays as arrays and not strings,
we need to subclass `PickleType`, and then use
`convert_sqlalchemy_type.register` much in the same way that graphene_sqlalchemy
does it internally for its other types.
"""
from typing import TYPE_CHECKING, Type, TypeAlias, Union
import sqlalchemy as sa

from ert_storage.database import IS_POSTGRES

__all__ = ["FloatArray", "StringArray", "IntArray"]

if TYPE_CHECKING or IS_POSTGRES:
    from sqlalchemy.dialects.postgresql import ARRAY

    FloatArray: ARRAY = ARRAY(sa.Float)
    StringArray: ARRAY = ARRAY(sa.String)
    IntArray: ARRAY = ARRAY(sa.Integer)
else:
    FloatArray = type("FloatArray", (sa.PickleType,), dict(sa.PickleType.__dict__))
    StringArray = type("StringArray", (sa.PickleType,), dict(sa.PickleType.__dict__))
    IntArray = type("IntArray", (sa.PickleType,), dict(sa.PickleType.__dict__))
