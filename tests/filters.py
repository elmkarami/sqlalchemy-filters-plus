from marshmallow import Schema, fields, validate

from sqlalchemy_filters.fields import DateField
from sqlalchemy_filters.fields import DateTimeField
from sqlalchemy_filters.fields import Field
from sqlalchemy_filters.fields import IntegerField
from sqlalchemy_filters.fields import StringField
from sqlalchemy_filters.filters import Filter as BaseFilter
from sqlalchemy_filters.filters import NestedFilter
from sqlalchemy_filters.operators import ContainsOperator
from sqlalchemy_filters.operators import EqualsOperator
from sqlalchemy_filters.operators import GTOperator
from sqlalchemy_filters.operators import IStartsWithOperator
from sqlalchemy_filters.operators import LTEOperator
from sqlalchemy_filters.operators import OrOperator
from sqlalchemy_filters.operators import StartsWithOperator
from tests.models import Article
from tests.models import User

filter_registry = set()


def patch_filters_session(session):
    for filter_class in filter_registry:
        filter_class.session = session


class Filter(BaseFilter):
    _abstract = True

    def __init_subclass__(cls, **kwargs):
        filter_registry.add(cls)


class EqualFilter(Filter):
    first_name = Field(lookup_operator=EqualsOperator)

    class Meta:
        model = User


class StartsWithFilter(Filter):
    first_name = Field(lookup_operator=StartsWithOperator)

    class Meta:
        model = User


class ContainsFilter(Filter):
    first_name = Field(lookup_operator=ContainsOperator)

    class Meta:
        model = User


class ContainsFKFilter(Filter):
    author_first_name = Field(
        field_name="user.first_name", lookup_operator=ContainsOperator
    )

    class Meta:
        model = Article


class Contains2FKFilter(ContainsFKFilter):
    author_last_name = Field(
        field_name="user.last_name", lookup_operator=ContainsOperator
    )

    class Meta:
        model = Article


class MultipleFKFilter(Filter):
    author_first_name = Field(
        field_name="user.first_name",
        lookup_operator=ContainsOperator,
        join=Article.user,
    )
    author_last_name_istarts = Field(
        field_name="user.last_name", lookup_operator=IStartsWithOperator
    )

    class Meta:
        model = Article


class TypedFilter(Filter):
    first_name = StringField()
    min_age = IntegerField(field_name="age", lookup_operator=GTOperator)
    until_birth_date = DateField(field_name="birth_date", lookup_operator=LTEOperator)
    created_at = DateTimeField(lookup_operator=EqualsOperator)

    class Meta:
        model = User


class MyNestedFilter(Filter):
    email = StringField(lookup_operator=ContainsOperator)
    nested1 = NestedFilter(TypedFilter, operator=OrOperator, flat=False)
    nested2 = NestedFilter(MultipleFKFilter, operator=OrOperator, flat=False)

    class Meta:
        model = User


class InheritMyNestedFilter(MyNestedFilter):
    class Meta:
        model = User


class AgeSchema(Schema):
    min_age = fields.Integer(validate=validate.Range(min=20))


class FirstNameOneOfwSchema(Schema):
    author_first_name = fields.String(validate=validate.OneOf(["john", "james"]))


class AgeMarshmallowFilter(MyNestedFilter):
    class Meta:
        model = User
        marshmallow_schema = AgeSchema


class FirstNameMarshmallowFilter(MyNestedFilter):
    nested2 = NestedFilter(
        MultipleFKFilter,
        operator=OrOperator,
        flat=False,
        marshmallow_schema=FirstNameOneOfwSchema,
    )

    class Meta:
        model = User
