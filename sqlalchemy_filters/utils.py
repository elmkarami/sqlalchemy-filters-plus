from datetime import datetime
from functools import wraps
from typing import Any

from sqlalchemy import text  # type: ignore
from sqlalchemy.orm import Query  # type: ignore
from sqlalchemy import __version__


SQLALCHEMY_VERSION = __version__
IS_SQLALCHEMY_1_4 = __version__.startswith("1.4")


class Empty:
    pass


def get_sqlalchemy_version():
    return


def is_none(value: Any) -> bool:
    return isinstance(value, type(None))


def empty_sql():
    return text("")


def get_already_joined_tables(query: Query) -> list:
    if IS_SQLALCHEMY_1_4:
        return [joins[0].parent.entity for joins in query._setup_joins]
    return [mapper.class_ for mapper in query._join_entities]


def to_timezone(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        value = func(self, *args, **kwargs)
        if isinstance(value, datetime):
            value = value.replace(tzinfo=value.tzinfo or self.timezone)
        return value

    return wrapper
