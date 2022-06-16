from datetime import datetime
from functools import wraps
from typing import Any

from sqlalchemy import text  # type: ignore
from sqlalchemy import __version__

SQLALCHEMY_VERSION = __version__
IS_SQLALCHEMY_1_4 = __version__[0] == "1" and __version__[2] >= "4"


if IS_SQLALCHEMY_1_4:
    from sqlalchemy.sql import coercions
    from sqlalchemy.sql import roles


class Empty:
    pass


def is_none(value: Any) -> bool:
    return isinstance(value, type(None))


def empty_sql():
    return text("")


def is_already_joined(query, model):
    if not IS_SQLALCHEMY_1_4:
        return model in [mapper.class_ for mapper in query._join_entities]
    if hasattr(query, "_setup_joins"):
        if model in [joins[0].parent.entity for joins in query._setup_joins]:
            return True
    if hasattr(query, "_legacy_setup_joins"):
        join_table = coercions.expect(roles.JoinTargetRole, model, legacy=True)
        return join_table in [_[0] for _ in query._legacy_setup_joins]


def to_timezone(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        value = func(self, *args, **kwargs)
        if isinstance(value, datetime):
            value = value.replace(tzinfo=value.tzinfo or self.timezone)
        return value

    return wrapper
