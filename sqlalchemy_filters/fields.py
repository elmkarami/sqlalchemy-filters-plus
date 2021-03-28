"""
This module defines all types of fields used by the filter classes.
"""
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timezone
from decimal import Decimal
from typing import Any
from typing import Callable
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union

from sqlalchemy import column  # type: ignore
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.elements import ColumnClause
from sqlalchemy.sql.elements import TextClause

from sqlalchemy_filters.exceptions import FieldMethodNotFound
from sqlalchemy_filters.exceptions import FieldValidationError
from sqlalchemy_filters.mixins import ForeignKeyFieldMixin
from sqlalchemy_filters.operators import BaseOperator
from sqlalchemy_filters.operators import EqualsOperator
from sqlalchemy_filters.utils import Empty
from sqlalchemy_filters.utils import empty_sql
from sqlalchemy_filters.utils import is_none
from sqlalchemy_filters.utils import to_timezone


class BaseField:
    """
    Base field class
    """

    def __init__(
        self,
        *,
        field_name: Optional[str] = None,
        lookup_operator: Optional[Type[BaseOperator]] = EqualsOperator,
        join: Optional[Union[Any, Tuple[Any, Any]]] = None,
        custom_column: Optional[ColumnClause] = None,
        data_source_name: Optional[str] = None,
        allow_none: Optional[bool] = False,
    ) -> None:
        """

        :param field_name: Field name of the model, can also refer to a field in a foreign key.
                            We don't not have to specify it if that field name that's defined with is the same as the
                            model attribute

                        >>> class MyFilter(Filter):
                        >>>     # field1 is not a attribute/field of the model
                        >>>     # hence we specified it explicitly
                        >>>     field1 = Field(field_name="column")
                        >>>     # field2 is an attribute/field of the model
                        >>>     # we don't have to explicitly declare it
                        >>>     field2 = Field()
                        >>>     field3 = Field(field_name="foreign_model.attribute")
                        >>>     ...

        :param lookup_operator: The operator class used to join the fields filtering together. Can only be AndOperator
                                or OrOperator.
        :param join: A Model to join the query with, can also be a tuple. This will be passed to the `join` method of
                    the SQLAlchemy Query object.
        :param custom_column: You can use a custom column to filter with. It can accept a string, a column or a Model
                             field

                        >>> from sqlalchemy import column
                        >>>
                        >>> class MyFilter(Filter):
                        >>>     field1 = Field(custom_column="my_column")
                        >>>     field2 = Field(custom_column=column("some_column"))
                        >>>     field3 = Field(custom_column=MyModel.field)
                        >>>     ...

        :param data_source_name: The key used to extract the value of the field from the data provided.
        :param allow_none: (default to ``False``): If set to `True` it allows filtering with None values. But Only if
                            the data contains the value `None`
        """
        self.field_name = field_name
        self.data_source_name = data_source_name
        self.lookup_operator = lookup_operator
        self.join = join or None
        self._column = custom_column
        self.parent = None
        self.allow_none = allow_none
        self.parent_filter = None

    def __set_name__(self, owner, name):
        self.public_name = name
        self.parent_filter = owner

    def __eq__(self, other):
        return {**self.__dict__, "parent_filter": None} == {
            **other.__dict__,
            "parent_filter": None,
        }

    def __deepcopy__(self, memo):
        obj = self.__class__()
        obj.__dict__ = dict((k, v) for k, v in self.__dict__.items())
        return obj

    def post_init(self, parent_filter):
        self.parent_filter = parent_filter
        self._set_column()

    def _set_column(self):
        if is_none(self._column):
            self._column = getattr(
                self.parent_filter.Meta.model, self.field_name or self.public_name
            )
        elif isinstance(self._column, str):
            self._column = column(self._column)

    def __get__(self, instance, owner):
        return self

    def validate(self, value) -> Any:
        """
        Validates the value

        :param value: value extracted from the original data
        :return: Sanitized or original value

        :raises: :attr:`FieldValidationError <sqlalchemy_filters.exceptions.FieldValidationError>` if validation fails.
                 This is used for custom validation.
        """
        return value

    def _apply_filter(self, filter_obj, value):
        if not isinstance(value, list):
            value = [value]
        return self.lookup_operator(self._column, value).to_sql()

    def get_data_source_name(self) -> str:
        """
        :return: Return the key to be used to look for the value of the field.
        """
        return self.data_source_name or self.public_name

    def get_field_value(self, data):
        """
        :param data: Data provided while instantiating the filter class
                    (pre-validation: :attr:`data <sqlalchemy_filters.filters.BaseFilter.data>`)
        :return: The field value from the data, if not found it returns `Empty` class.
        """
        return data.get(self.get_data_source_name(), Empty)

    def get_field_value_for_filter(self, filter_obj):
        """
        Extracts the value of the field from the
        :attr:`validated_data <sqlalchemy_filters.filters.BaseFilter.validated_data>`.

        :param filter_obj: The filter instance
        :return: The field value from the data, if not found it returns `Empty` class.
        """
        return self.get_field_value(filter_obj.validated_data)

    def apply_filter(self, filter_obj):
        """
        Applies the filtering part using the operator class and the value extracted using
                :meth:`get_field_value_for_filter`.

        :param filter_obj: The Filter instance
        :return: SQLAlchemy `BinaryExpression`
        """
        value = self.get_field_value_for_filter(filter_obj)
        if value is Empty:
            return empty_sql()
        elif value is None and not self.allow_none:
            return empty_sql()

        return self._apply_filter(filter_obj, value)


class MethodField(BaseField):
    """
    Field used to delegate the filtering logic to a Filter method or a standalone function.

    :Warning: The :attr:`MethodField` does not provide any validation and consumes any values extracted from
            the :attr:`data <sqlalchemy_filters.filters.BaseFilter.data>` field.
    """

    #:
    method: Callable

    def __init__(
        self,
        *,
        method: Union[Callable, str],
        data_source_name=None,
    ):
        """
        :param method: A callable that accepts a single value which is the field value.
        :param data_source_name: The key used to extract the value of the field from the data provided.
        """
        super().__init__(data_source_name=data_source_name)
        self.method = method

    def __deepcopy__(self, memo):
        obj = self.__class__(method=self.method)
        obj.__dict__ = dict((k, v) for k, v in self.__dict__.items())
        return obj

    def _set_column(self):
        pass

    def post_init(self, parent_filter):
        super().post_init(parent_filter)
        self.extract_method(parent_filter)

    def extract_method(self, filter_obj) -> Callable:
        """
        Extracts the method from the filter instance if found, otherwise checks if :attr:`method` is a callable

        :param filter_obj: the Filter instance
        :return: Callable used to apply the filtering part of the current field.
        """
        if callable(self.method):
            method = self.method
        else:
            method = getattr(filter_obj, self.method or "", None)
        if not method:
            raise AttributeError(
                f"{filter_obj.__class__.__name__} has not method {self.method}"
            )

        if not callable(method):
            raise FieldMethodNotFound(
                parent_filter=filter_obj.__class__,
                field_name=self.public_name,
                method_name=self.method,
            )
        return method

    def get_field_value_for_filter(self, filter_obj):
        """
        Extracts the value of the field from the
        :attr:`data <sqlalchemy_filters.filters.BaseFilter.data>`.

        :param filter_obj: The filter instance
        :return: The field value from the data, if not found it returns `Empty` class.
        """
        return self.get_field_value(filter_obj.data)

    def _apply_filter(self, filter_obj, value) -> Union[TextClause, BinaryExpression]:
        method = self.extract_method(filter_obj)
        sql_expression = method(value)
        if is_none(sql_expression):
            raise ValueError(
                f"{filter_obj.__class__.__name__}.{self.method} must return a sql expression."
            )
        return sql_expression


class Field(ForeignKeyFieldMixin, BaseField):
    """
    This is the Default field instance that can be instantiated as used as a filter field.
    """


class TypedField(Field):
    type_: Type
    error_message: str = "Expected to be of type {type_}"

    def validate(self, value: Any) -> Any:
        try:
            return self.type_(value)
        except Exception:
            raise FieldValidationError(
                self.error_message.format(type_=self.type_.__name__)
            )


class IntegerField(TypedField):
    type_ = int


class DecimalField(TypedField):
    type_ = Decimal


class FloatField(TypedField):
    type_ = float


class StringField(TypedField):
    type_ = str


class BooleanField(TypedField):
    type_ = bool


class TimestampField(FloatField):
    is_timestamp = True

    def __init__(self, *, timezone=timezone.utc, **kwargs):
        self.timezone = timezone
        super().__init__(**kwargs)

    @to_timezone
    def validate(self, value: Union[int, float]) -> datetime:
        value = super().validate(value)
        return datetime.fromtimestamp(value, self.timezone)


class BaseDateField(TimestampField):
    type_: Union[date, datetime]

    def __init__(self, *, date_format: str = "%Y-%m-%d", is_timestamp=False, **kwargs):
        """
        :param date_format: date_format that can be accepted by the `datetime.strptime` method.
        :param is_timestamp: True if it's intented to be used as a timestamp
        :param kwargs:
        """
        self.date_format = date_format
        self.is_timestamp = is_timestamp
        super().__init__(**kwargs)

    @to_timezone
    def validate(self, value: Union[str, datetime, date, int, float]) -> datetime:
        if self.is_timestamp:
            return super().validate(value)
        try:
            return datetime.strptime(str(value), self.date_format)
        except ValueError as exc:
            raise FieldValidationError(str(exc))


class DateTimeField(BaseDateField):
    def __init__(self, *, datetime_format: str = "%Y-%m-%d", **kwargs):
        super().__init__(date_format=datetime_format, **kwargs)

    @to_timezone
    def validate(self, value: Union[str, datetime, date, int, float]) -> datetime:
        if isinstance(value, datetime):
            return value
        elif isinstance(value, date):
            return datetime.combine(value, time())
        value = super().validate(value)
        return value


class DateField(BaseDateField):
    def validate(self, value: Union[float, int, str, datetime, date]) -> date:
        return super().validate(value).date()
