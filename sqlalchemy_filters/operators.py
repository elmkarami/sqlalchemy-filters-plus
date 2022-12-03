"""
This module contains the defined operators used to construct simple or more complex sql queries.
"""

from functools import wraps
from typing import Callable, List, Optional, Type, TypeVar

from sqlalchemy import column, func
from sqlalchemy.sql.elements import BinaryExpression, ClauseElement, TextClause
from sqlalchemy.sql.operators import (
    and_,
    between_op,
    contains_op,
    endswith_op,
    eq,
    ge,
    gt,
    in_op,
    is_,
    isnot,
    le,
    lt,
    or_,
    startswith_op,
)

from sqlalchemy_filters.exceptions import InvalidParamError
from sqlalchemy_filters.utils import SQLALCHEMY_VERSION, empty_sql

T = TypeVar("T")
V = TypeVar("V", str, ClauseElement)


def register_operator(
    cls: Optional[Type] = None, *, sql_operator: Optional[Callable] = None
):
    """Register a class as an operator class.

    :param cls: Registering an operator without providing a builtin SQLAlchemy builtin operator.
    :param sql_operator: A sqlalchemy operator or a custom callable that acts as an sqlalchemy operator.
    """

    def decorator(clazz: Type):
        clazz.operator = property(lambda self: sql_operator)
        return clazz

    if cls is not None:
        return decorator(cls)

    return decorator


def sa_1_4_compatible(f):
    """Decorator for the method :attr:`BaseOperator.to_sql`

    Since `TextClause` does not support `BinaryExpression` as a left operand in SqlAlchemy 1.4,
    we revert the left/right sides of the operation

    Ex:

        >>> # raises: unsupported operand type(s) for | TextClause and BinaryExpression
        >>> text("1 = 1") | (column("x") == 1)

    would change to:

        >>> (column("x") == 1) | text("1 = 1")

    """
    if not SQLALCHEMY_VERSION.startswith("1.4"):
        return f

    @wraps(f)
    def wrapper(self):
        sql_exp = self.get_sql_expression()
        if all(
            map(
                lambda x: isinstance(x, TextClause) and empty_sql().compare(x),
                [*self.params, sql_exp],
            )
        ):
            return empty_sql()

        if isinstance(sql_exp, TextClause):
            return self.operator(*self.params, sql_exp)
        return f(self)

    return wrapper


class BaseOperator:
    """Base operator class.

    Inherit from this class to create custom operators.
    """

    #: Anything that can be used an operand for the sqlalchemy operators.
    sql_expression = None
    #: A list of parameters or operands for the operator
    params: list
    #: sqlalchemy operator, but can also be any callable that accepts :attr:`sql_expression`
    #: handled by sqlalchemy operators
    operator: Callable

    def __init_subclass__(cls, **kwargs):
        cls.to_sql = sa_1_4_compatible(cls.to_sql)

    def __init__(self, sql_expression: V, params: Optional[List[T]] = None):
        self.sql_expression = sql_expression
        self.params = params or []
        self.check_params(self.params)

    def get_sql_expression(self) -> ClauseElement:
        """Returns a `ClauseElement` depends on the :attr:`sql_expression` is

        :return:
        """
        if type(self.sql_expression) is str:
            return column(self.sql_expression)
        return self.sql_expression

    def to_sql(self) -> BinaryExpression:
        """
        Execute the operator against the database.
        """
        return self.operator(self.get_sql_expression(), *self.params)

    @classmethod
    def check_params(cls, params: list) -> None:
        """Validates the params.

        Can be refined by subclasses to define a custom validation for :attr:`params`

        :param params: operands for the operator.
        :raises: :attr:`InvalidParamError <sqlalchemy_filters.exceptions.InvalidParamError>` if checking failed.
        """
        if not isinstance(params, list):
            raise InvalidParamError(
                f"{cls.__name__}.params expected to be a list, got {type(params).__name__}."
            )


@register_operator(sql_operator=is_)
class IsOperator(BaseOperator):
    """`is` sql operator."""


@register_operator(sql_operator=isnot)
class IsNotOperator(BaseOperator):
    pass


@register_operator(sql_operator=is_)
class IsEmptyOperator(BaseOperator):
    params = [None]


@register_operator(sql_operator=isnot)
class IsNotEmptyOperator(BaseOperator):
    params = [None]


@register_operator(sql_operator=in_op)
class INOperator(BaseOperator):
    def to_sql(self) -> BinaryExpression:
        return self.operator(self.get_sql_expression(), self.params)


@register_operator(sql_operator=eq)
class EqualsOperator(BaseOperator):
    pass


@register_operator(sql_operator=between_op)
class RangeOperator(BaseOperator):
    @classmethod
    def check_params(cls, params: list) -> None:
        super().check_params(params)
        if len(params) != 2:
            raise InvalidParamError(
                f"{cls.__name__}.params should have exactly 2 values, got {len(params)}."
            )


@register_operator(sql_operator=le)
class LTEOperator(BaseOperator):
    pass


@register_operator(sql_operator=lt)
class LTOperator(BaseOperator):
    pass


@register_operator(sql_operator=ge)
class GTEOperator(BaseOperator):
    pass


@register_operator(sql_operator=gt)
class GTOperator(BaseOperator):
    pass


@register_operator(sql_operator=and_)
class AndOperator(BaseOperator):
    pass


@register_operator(sql_operator=or_)
class OrOperator(BaseOperator):
    pass


@register_operator(sql_operator=contains_op)
class ContainsOperator(BaseOperator):
    pass


@register_operator(sql_operator=contains_op)
class IContainsOperator(BaseOperator):
    def to_sql(self):
        return self.operator(
            func.lower(self.get_sql_expression()), func.lower(*self.params)
        )


@register_operator(sql_operator=startswith_op)
class StartsWithOperator(BaseOperator):
    pass


@register_operator(sql_operator=startswith_op)
class IStartsWithOperator(StartsWithOperator):
    def to_sql(self):
        return self.operator(
            func.lower(self.get_sql_expression()), func.lower(*self.params)
        )


@register_operator(sql_operator=endswith_op)
class EndsWithOperator(BaseOperator):
    pass


@register_operator(sql_operator=endswith_op)
class IEndsWithOperator(BaseOperator):
    def to_sql(self) -> BinaryExpression:
        return self.operator(
            func.lower(self.get_sql_expression()), func.lower(*self.params)
        )
