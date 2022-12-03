from datetime import datetime
from functools import wraps
from typing import Any

from sqlalchemy import text  # type: ignore
from sqlalchemy import __version__
from sqlalchemy.orm.attributes import InstrumentedAttribute

SQLALCHEMY_VERSION = __version__
IS_GTE_1_4 = __version__[0] > "1" or (__version__[0] == "1" and __version__[2] >= "4")


if IS_GTE_1_4:
    from sqlalchemy.sql import coercions, roles


class Empty:
    pass


def is_none(value: Any) -> bool:
    return isinstance(value, type(None))


def empty_sql():
    return text("")


class SQLAlchemyGTE14JoinDetector:
    def __init__(self, query):
        self.query = query

    def _check_setup_joins(self, model):
        setup_joins = getattr(self.query, "_setup_joins", [])
        return model in [joins[0].parent.entity for joins in setup_joins]

    def _check_instrumented_attribute(self, model, joins):
        if not joins:
            return False
        for join in joins:
            if isinstance(join, InstrumentedAttribute):
                if model == join.comparator.entity.class_:
                    return True
        return False

    def _check_legacy_setup_joins(self, model):
        legacy_setup_joins = getattr(self.query, "_legacy_setup_joins", [])
        joins = [_[0] for _ in legacy_setup_joins]
        join_table = coercions.expect(roles.JoinTargetRole, model, legacy=True)
        return self._check_instrumented_attribute(model, joins) or join_table in joins

    def has_join_for(self, model) -> bool:
        return self._check_setup_joins(model) or self._check_legacy_setup_joins(model)


class SQLAlchemyLT14JoinDetector:
    def __init__(self, query):
        self.query = query

    def has_join_for(self, model) -> bool:
        return model in [mapper.class_ for mapper in self.query._join_entities]


def is_already_joined(query, model):
    if IS_GTE_1_4:
        return SQLAlchemyGTE14JoinDetector(query).has_join_for(model)
    return SQLAlchemyLT14JoinDetector(query).has_join_for(model)


def to_timezone(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        value = func(self, *args, **kwargs)
        if isinstance(value, datetime):
            value = value.replace(tzinfo=value.tzinfo or self.timezone)
        return value

    return wrapper
