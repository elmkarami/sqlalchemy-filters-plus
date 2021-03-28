from typing import Any

from sqlalchemy import text  # type: ignore


class Empty:
    pass


def is_none(value: Any) -> bool:
    return isinstance(value, type(None))


def empty_sql():
    return text("")
