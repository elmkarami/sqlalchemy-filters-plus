"""
Modules defines the Filter and NestedFilter classes
"""
from collections import OrderedDict
from copy import deepcopy
from functools import reduce
from typing import Any, Dict, List, Optional, Type, Union

from sqlalchemy import DECIMAL, Boolean, Date, DateTime, Float, Integer, String
from sqlalchemy.sql.elements import UnaryExpression

from sqlalchemy_filters.exceptions import (
    FieldValidationError,
    FilterNotCompatible,
    FilterValidationError,
    OrderByException,
)
from sqlalchemy_filters.fields import (
    BooleanField,
    DateField,
    DateTimeField,
    DecimalField,
    Empty,
    Field,
    FloatField,
    IntegerField,
    MethodField,
    StringField,
)
from sqlalchemy_filters.mixins import MarshmallowValidatorFilterMixin
from sqlalchemy_filters.operators import AndOperator, BaseOperator
from sqlalchemy_filters.paginator import Paginator
from sqlalchemy_filters.utils import empty_sql, is_already_joined, is_none

FILTERS_MAPPING = {
    String: StringField,
    Integer: IntegerField,
    Float: FloatField,
    DECIMAL: DecimalField,
    Date: DateField,
    DateTime: DateTimeField,
    Boolean: BooleanField,
}


def check_has_field(model, field_name, filter_name):
    if not hasattr(model, field_name):
        raise AttributeError(
            f"Error defining filter {filter_name}: "
            f"{model.__name__} model has not attribute called '{field_name}'"
        )


class NestedFilter:
    """
    NestedFilters are a way to use already defined filter classes as fields and build complex queries.
    """

    #: The filter class that will be used as a :attr:`NestedFilter` field
    filter_class: Type["Filter"]
    #: How to join the inner fields of the :attr:`filter_class`
    operator: Type[BaseOperator] = AndOperator
    #: Operator describes how to join the inner fields of the NestedFilter and the field of the parent filter
    #: If not defined the operator of the parent filter will be used
    outer_operator: Optional[Type[BaseOperator]]
    #: If True, means that the nested filter should get the value of its fields from root level of the data
    #: If False, the values will be extracted using either :attr:`data_source_name` if defined or the name of field in
    #: the parent filter:
    #:
    #:    >>> # data for the nested filter will be extracted from the key `custom_field`
    #:    >>> custom_field = NestedFilter(MyFilter, flat=False)
    flat: bool = False
    #: key to look for the nested filter fields from the data, this is ignored if :attr:`flat` is True.
    data_source_name: Optional[str] = None
    #: Custom Marshmallow for validation
    marshmallow_schema = None

    def __init__(
        self,
        filter_class: Type["Filter"],
        operator: Type[BaseOperator] = AndOperator,
        outer_operator: Optional[Type[BaseOperator]] = None,
        flat: bool = True,
        data_source_name: Optional[str] = None,
        marshmallow_schema=None,
    ):
        self.filter_class = filter_class
        self.operator = operator
        self.outer_operator = outer_operator
        self.flat = flat
        self.data_source_name = data_source_name
        self.marshmallow_schema = marshmallow_schema

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __deepcopy__(self, memodict):
        obj = self.__class__(filter_class=self.filter_class, operator=self.operator)
        obj.__dict__ = dict((k, v) for k, v in self.__dict__.items())
        return obj

    def __set_name__(self, owner, name):
        self.public_name = name

    def get_data_source_name(self) -> str:
        """
        :return: key used to extract the data that will be used to validate and filter with.
        """
        return self.data_source_name or self.public_name

    def get_data(self, parent_filter_obj: "BaseFilter") -> dict:
        """
        How to extract the data from the parent filter object.

        :param parent_filter_obj: The parent filter object instance.
        :return: data that will be passed to the :attr:`filter_class`
        """
        if self.flat:
            return parent_filter_obj.data
        value = parent_filter_obj.data.get(self.get_data_source_name())
        if value and not isinstance(value, dict):
            raise ValueError(
                f"The value of the key {self.get_data_source_name()} inside "
                f"{parent_filter_obj.__class__.__name__}.data is expected to be a dict since flat is set to False, "
                f"but {type(value).__name__} found. "
                f"Or it could be that you are mismatching data_source_name param with the field attribute name "
                f"{self.public_name}."
            )
        return value or {}

    def build_filter_object(
        self, parent_filter_obj: "BaseFilter", data: dict
    ) -> "BaseFilter":
        return self.filter_class(
            data=data,
            operator=self.operator,
            session=parent_filter_obj.session,
            marshmallow_schema=self.marshmallow_schema
            or parent_filter_obj.marshmallow_schema,
        )

    def validate(self, parent_filter_obj: "BaseFilter", data: dict):
        filter_object = self.build_filter_object(
            parent_filter_obj=parent_filter_obj, data=data
        )
        filter_object.validate()

    def apply(self, parent_filter_obj: "BaseFilter"):
        """
        Gets the data from the parent filter then apply the filter for the :attr:`filter_class`

        :param parent_filter_obj: The parent filter object instance.
        :return: the sql expression that will be combined with :attr:`parent_filter_obj`'s inner fields.
        """
        data = self.get_data(parent_filter_obj)
        if not data:
            return empty_sql()
        filter_obj = self.build_filter_object(
            parent_filter_obj=parent_filter_obj, data=data
        )
        return filter_obj.apply_all().self_group()


class FilterType(type):
    def __new__(mcs, name, bases, attrs):
        fields = {}
        nested = {}
        method_fields = {}
        for field_name, field in attrs.items():
            if isinstance(field, MethodField):
                method_fields[field_name] = field
            elif isinstance(field, Field):
                fields[field_name] = field
            elif isinstance(field, NestedFilter):
                nested[field_name] = field

        mcs.check_model_presence(name, attrs)
        meta = attrs.get("Meta")
        _abstract = attrs.get("_abstract")
        if not _abstract:
            mcs.check_model_compatibility(name, meta.model, bases, nested.values())
            attrs["_model"] = meta.model
            mcs.check_field_name(name, meta.model, fields)

        declared_fields = getattr(meta, "fields", [])
        attrs["session"] = getattr(meta, "session", None)
        attrs["_order_by"] = getattr(meta, "order_by", None)
        attrs["_limit"] = getattr(meta, "page_size", None)
        attrs["_offset"] = 0
        attrs["marshmallow_schema"] = getattr(meta, "marshmallow_schema", None)
        attrs["declared_fields"] = declared_fields
        _class: Filter = super().__new__(mcs, name, bases, attrs)  # noqa

        if not hasattr(_class, "fields"):
            _class.fields = {}
        if not hasattr(_class, "nested"):
            _class.nested = {}
        if not hasattr(_class, "method_fields"):
            _class.method_fields = {}

        _class.fields = deepcopy({**_class.fields, **fields})
        _class.nested = deepcopy({**_class.nested, **nested})
        _class.method_fields = deepcopy({**_class.method_fields, **method_fields})
        _class.create_missing_fields(declared_fields)
        if not _abstract:
            for field in list(_class.fields.values()) + list(
                _class.method_fields.values()
            ):
                field.post_init(_class)
        return _class

    @classmethod
    def check_model_presence(mcs, name, attrs):
        meta = attrs.get("Meta")
        _abstract = attrs.get("_abstract")
        if not _abstract and not meta:
            raise AttributeError(f"Filter {name} does not define a Meta class.")
        if not _abstract and not hasattr(meta, "model"):
            raise AttributeError(f"Filter '{name}.Meta' does not have a model.")

    @classmethod
    def check_model_compatibility(mcs, name, model, bases, nested):
        for base in bases:
            meta = getattr(base, "Meta", None)
            base_model = meta and meta.model
            if base_model and model != base_model:
                raise FilterNotCompatible(
                    class_name=name, model=model, base_filter=base
                )
        for nested in nested:
            if nested.filter_class.Meta.model != model:
                raise FilterNotCompatible(
                    class_name=name, model=model, base_filter=nested.filter_class
                )

    @classmethod
    def check_field_name(mcs, name: str, model, fields: Dict[str, Field]):
        for fn, field in fields.items():
            if field.is_foreign_key:
                continue
            check_has_field(
                model=model, field_name=field.field_name or fn, filter_name=name
            )

    @classmethod
    def __prepare__(mcs, name, bases):
        return OrderedDict()


class BaseFilter(metaclass=FilterType):
    """
    Base filter that any other filter class should inherit from.
    """

    #: If true, no check is applied to the filter class
    _abstract = True
    #: SQLAlchemy model
    _model = None
    #: Fields declared using any class that inherits from :attr:`Filter`
    fields: Dict[str, Field]
    #: NestedFilter
    nested: Dict[str, NestedFilter]
    #: Method fields
    method_fields: Dict[str, MethodField]
    #: Ordering the query
    _order_by: Any = None
    #: Limit of the query: Equivalent to query.limit(limit)
    _limit: Optional[int] = None
    #: Offset of the query: Equivalent to query.offset(offset)
    _offset: Optional[int] = None
    #: Operator describing how to join the fields
    operator = Type[BaseOperator]
    #: Flag to whether the data was validated or not
    validated: bool
    #: Contains the original data passed to the constructor
    data: dict
    #: Contains the validated data extracted from :attr:`data`
    validated_data: Dict
    #: sqlalchemy session object
    session: Any = None
    #: marshmallow schema class
    marshmallow_schema: Any = None

    def __init__(
        self,
        *,
        data: dict,
        operator: Type[BaseOperator] = AndOperator,
        query=None,
        session=None,
        marshmallow_schema=None,
    ):
        self.data = data
        self.validated_data = {}
        self.operator = operator
        self.query = query
        self.session = session or self.session
        self.set_query()
        self.marshmallow_schema = marshmallow_schema or self.marshmallow_schema

    @classmethod
    def extract_declared_field(
        cls,
        fields: Dict[str, Union[Field, NestedFilter, MethodField]],
    ) -> Dict[str, Union[Field, NestedFilter, MethodField]]:
        # fields is not defined or empty
        if not cls.declared_fields:
            return fields

        declared = {}
        for field_name, field in fields.items():
            if field_name in cls.declared_fields:
                declared[field_name] = field

        return declared

    @classmethod
    def create_missing_fields(
        cls,
        declared_fields: List[str],
    ):
        for field_name in declared_fields:
            if field_name not in [
                *cls.fields.keys(),
                *cls.nested.keys(),
                *cls.method_fields.keys(),
            ]:
                check_has_field(
                    model=cls.Meta.model,
                    field_name=field_name,
                    filter_name=cls.__name__,
                )
                model_column = getattr(cls.Meta.model, field_name)
                field = FILTERS_MAPPING.get(model_column.type.__class__)
                if not field:
                    raise AttributeError(
                        f"could not map type '{model_column.type}' for field '{field_name}'. "
                        f"Please define it as a field in the filter class or remove it from the declared fields."
                    )
                field_obj = field(field_name=field_name)
                field_obj.__set_name__(owner=cls, name=field_name)
                cls.fields[field_name] = field_obj

    @classmethod
    def _get_joins(cls):
        joins = []
        for _, field in cls.extract_declared_field(cls.fields).items():
            joins.extend(field.joins)
        for _, field in cls.extract_declared_field(cls.nested).items():
            joins.extend(field.filter_class._get_joins())
        return joins

    def _apply_join(self, query):
        # remove duplicates and preserve order
        joins = list(OrderedDict.fromkeys(self._get_joins()))
        for join in joins:
            if is_already_joined(query, join[0]):
                continue
            query = query.join(join)
        return query

    def set_query(self):
        """
        Sets the query to the current filter object (called at the :meth:`__init__` method).

        :return: None
        """
        if not self.query and not self.session:
            raise AttributeError(
                f"Can not find session for filter '{self.__class__.__name__}'. Please either define a SQLAlchemy "
                f"session at the meta class, at instantiation level or provide a query when instantiating the Filter."
            )
        self.query = self.query or self.session.query(self.Meta.model).filter()

    def validate_nested(self):
        """
        Validate all :attr:`NestedFilters <sqlalchemy_filters.filters.NestedFilter>` fields.

        :raise: :attr:`FilterValidationError <sqlalchemy_filters.exceptions.FilterValidationError>`

        :return: None
        """
        errors = []
        for field in self.nested.values():
            try:
                field.validate(parent_filter_obj=self, data=field.get_data(self))
            except FieldValidationError as exc:
                exc.set_field_name(field.get_data_source_name())
                errors.append(exc)
        if errors:
            raise FilterValidationError(field_errors=errors)

    def validate_fields(self):
        """
        Validates the data by calling :meth:`validate <sqlalchemy_filters.fields.BaseField.validate>` of each field.

        Each validated value is put back inside :attr:`validated_data` using the return of field method
        :meth:`get_data_source_name <sqlalchemy_filters.fields.BaseField.get_data_source_name>` as a key.
        That value will be used as as input to the operator of the corresponding field.

        :raise: :attr:`FilterValidationError <sqlalchemy_filters.exceptions.FilterValidationError>`

        :return: None
        """
        errors = []
        for field in self.fields.values():
            value = field.get_field_value(self.data)
            if value is Empty:
                continue
            try:

                self.validated_data[field.get_data_source_name()] = field.validate(
                    value
                )
            except FieldValidationError as exc:
                exc.set_field_name(field.get_data_source_name())
                errors.append(exc)
        if errors:
            raise FilterValidationError(field_errors=errors)

    def validate(self):
        """
        Calls :attr:`validate_fields` and :attr:`validate_nested`.
        If no error is raised, the :attr:`validated` attribute is set to `True`

        :return: None
        """
        self.validate_fields()
        self.validate_nested()
        self.validated = True

    def get_expression(self, field_filter):
        if hasattr(field_filter, "apply_filter"):
            return field_filter.apply_filter(self)
        return field_filter

    def apply_fields(self):
        """
        Calls :meth:`apply_filter <sqlalchemy_filters.fields.BaseField.apply_filter>` of each field and join them
        using the defined :attr:`operator`

        :return: SQLAlchemy `BinaryExpression`
        """
        fields = self.extract_declared_field(self.fields)
        if not fields:
            return empty_sql()
        if len(fields.values()) == 1:
            return list(self.fields.values())[0].apply_filter(self)
        r = reduce(
            lambda f1, f2: self.operator(
                sql_expression=self.get_expression(f1), params=[self.get_expression(f2)]
            ).to_sql(),
            fields.values(),
        )
        return r

    def apply_nested(self, filters):
        """
        Calls apply filter of each field and join them using the defined :attr:`operator`

        :param filters: The return value of :meth:`apply_fields`
        :return: SQLAlchemy `BinaryExpression`
        """
        for nested in self.extract_declared_field(self.nested).values():
            operator = nested.outer_operator or self.operator
            filters = operator(nested.apply(self), [filters]).to_sql()
        return filters

    def apply_methods(self, filters):
        """
        Calls :meth:`apply_filter <sqlalchemy_filters.fields.MethodField.apply_filter>` of each field and join them

        :param filters: The return value of :meth:`apply_fields`
        :return: SQLAlchemy `BinaryExpression`
        """
        for method_field in self.extract_declared_field(self.method_fields).values():
            filters = self.operator(method_field.apply_filter(self), [filters]).to_sql()
        return filters

    def apply_all(self):
        """
        Validates the :attr:`data` and applies all the fields.

        This method can be used to get the sqlalchemy `BinaryExpression` without having to construct a SQLAlchemy
        `Query` object.

        :return: SQLAlchemy `BinaryExpression`
        """
        self.validate()
        return self.apply_methods(self.apply_nested(self.apply_fields()))

    def _parse_order_by(self, _order_by):
        if isinstance(_order_by, UnaryExpression):
            return _order_by
        if not isinstance(_order_by, str):
            return None
        _order_by = _order_by.strip()
        field = getattr(self._model, _order_by.replace("-", ""), None)
        if not field:
            raise OrderByException(
                f"{self._model.__name__} does not have a field called "
                f"'{_order_by.replace('-', '')}' to use in an ORDER BY clause."
            )
        return getattr(field, "desc" if _order_by.startswith("-") else "asc")()

    def order_by(self, query):
        """
        Order the query by the specified `order_by` in the Meta class
        :param query: SQLAlchemy `Query` object.
        :return: Ordered SQLAlchemy `Query` object.
        """
        order_by = self.data.get("order_by", self._order_by)
        if is_none(order_by):
            return query
        if isinstance(order_by, str):
            order_by = [
                self._parse_order_by(ob)
                for ob in order_by.split(",")
                if ob and ob.strip()
            ]
        elif isinstance(order_by, (list, tuple)):
            order_by = [self._parse_order_by(ob) for ob in order_by]
        else:
            order_by = [self._parse_order_by(order_by)]
        order_by = [ob for ob in order_by if not is_none(ob)]
        if not order_by:
            return query
        return query.order_by(*order_by)

    def paginate(self) -> Paginator:
        """
        Creates a paginator that does all the work to slice the queries into a
        :attr:`Paginator <sqlalchemy_filters.paginator.Paginator>` object.

        :return: Return a :attr:`Paginator <sqlalchemy_filters.paginator.Paginator>`
        """
        page_size = int(self.data.get("page_size") or self._limit or 0)
        # Offset starts at 0
        page = int(self.data.get("page") or 1)
        if page < 1:
            page = 1
        if page_size <= 0:
            page_size = 0

        return Paginator(query=self.apply(), page=page, page_size=page_size)

    def apply(self):
        """
        Applies all fields, then using that result to filter the query then apply the joining of any potentiel foreign
        keys.

        :return: SQLAlchemy `Query` object.
        """
        filters = self.apply_all()
        query = self.query.filter(filters)
        query = self._apply_join(query)
        query = self.order_by(query)
        return query


class Filter(MarshmallowValidatorFilterMixin, BaseFilter):
    """
    Filter class.

    Makes use of MarshmallowValidatorFilterMixin to add the marshmallow validation capability.
    """

    _abstract = True
