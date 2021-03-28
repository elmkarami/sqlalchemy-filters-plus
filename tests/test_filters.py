from datetime import date
from datetime import datetime
from datetime import timezone
from unittest.mock import Mock

import pytest

from marshmallow import ValidationError, Schema, fields

from sqlalchemy_filters import Field
from sqlalchemy_filters import Filter
from sqlalchemy_filters import NestedFilter
from sqlalchemy_filters.exceptions import FilterValidationError
from sqlalchemy_filters.operators import AndOperator
from sqlalchemy_filters.operators import OrOperator
from sqlalchemy_filters.operators import GTEOperator
from sqlalchemy_filters.utils import empty_sql
from sqlalchemy_filters.fields import StringField
from sqlalchemy_filters.fields import IntegerField
from sqlalchemy_filters.fields import MethodField
from tests.factories import ArticleFactory
from tests.factories import UserFactory
from tests.filters import ContainsFilter
from tests.filters import ContainsFKFilter
from tests.filters import Contains2FKFilter
from tests.filters import EqualFilter
from tests.filters import MultipleFKFilter
from tests.filters import MyNestedFilter
from tests.filters import StartsWithFilter
from tests.filters import TypedFilter
from tests.filters import AgeSchema
from tests.filters import InheritMyNestedFilter
from tests.filters import AgeMarshmallowFilter
from tests.filters import FirstNameMarshmallowFilter
from tests.models import User
from tests.utils import compares_expressions


def test_no_meta_class_attached():
    with pytest.raises(AttributeError) as exc:

        class _(Filter):
            age = Field()

    assert exc.value.args == ("Filter _ does not define a Meta class.",)


def test_no_model_attached():
    with pytest.raises(AttributeError) as exc:

        class _(Filter):
            age = Field()

            class Meta:
                pass

    assert exc.value.args == ("Filter '_.Meta' does not have a model.",)


def test_not_session_attached():
    with pytest.raises(AttributeError) as exc:

        class _(Filter):
            age = Field()

            class Meta:
                model = User

        _(data={})

    assert exc.value.args == (
        "Can not find session for filter '_'. Please either define a SQLAlchemy session at the meta class, "
        "at instantiation level or provide a query when instantiating the Filter.",
    )


def test_session_attached(db_session):
    class F(Filter):
        age = Field()

        class Meta:
            model = User
            session = db_session

    user = UserFactory()
    f = F(data={})
    assert f.apply().all() == [user]


@pytest.mark.parametrize("ma_schema", [None, object()])
def test_marshmallow_schema_is_set_correctly(ma_schema):
    class F(Filter):
        age = Field()

        class Meta:
            model = User
            marshmallow_schema = ma_schema

    assert F.marshmallow_schema is ma_schema


@pytest.mark.parametrize(
    "field_name, expected",
    [
        ["not_a_field", "not_a_field"],
        [None, "f"],
    ],
)
def test_field_name_not_in_model(field_name, expected):
    with pytest.raises(AttributeError) as exc:

        class _(Filter):
            f = Field(field_name=field_name)

            class Meta:
                model = User

    assert (
        str(exc.value)
        == f"Error defining filter _: User model has not attribute called '{expected}'"
    )


def test_set_meta_class_fields():
    class F(Filter):
        name = Field(field_name="first_name")
        t = NestedFilter(MyNestedFilter)
        method = MethodField(method="some_method")
        email = Field()

        def some_method(self, value):
            pass

        class Meta:
            model = User
            fields = ["age", "name"]

    assert set(F.fields.keys()) == {"age", "name", "email"}
    assert set(F.extract_declared_field(F.fields).keys()) == {"age", "name"}
    assert set(F.extract_declared_field(F.nested).keys()) == set()
    assert set(F.extract_declared_field(F.method_fields).keys()) == set()

    class F2(F):
        t2 = MethodField(method=lambda x: x)

        class Meta:
            model = User
            fields = ["age", "t", "method"]

    assert set(F2.fields.keys()) == {"age", "name", "email"}
    assert set(F2.nested.keys()) == {"t"}
    assert set(F2.method_fields.keys()) == {"method", "t2"}

    assert set(F2.extract_declared_field(F2.fields).keys()) == {"age"}
    assert set(F2.extract_declared_field(F2.nested).keys()) == {"t"}
    assert set(F2.extract_declared_field(F2.method_fields).keys()) == {"method"}


def test_set_meta_class_field_does_not_exist():
    with pytest.raises(AttributeError) as exc:

        class _(Filter):
            name = Field(field_name="first_name")

            class Meta:
                model = User
                fields = ["x", "name"]

    assert (
        str(exc.value)
        == "Error defining filter _: User model has not attribute called 'x'"
    )


def test_set_meta_class_field_does_not_map():
    with pytest.raises(AttributeError) as exc:

        class _(Filter):
            name = Field(field_name="first_name")

            class Meta:
                model = User
                fields = ["last_login_time", "name"]

    assert str(exc.value) == (
        "could not map type 'TIME' for field 'last_login_time'. "
        "Please define it as a field in the filter class or "
        "remove it from the declared fields."
    )


def test_override_fields_in_inheritance(db_session):
    class F1(Filter):
        email = StringField()

        class Meta:
            model = User
            session = db_session

    class F2(F1):
        email = IntegerField()

        class Meta:
            model = User
            session = db_session

    assert len(F2.fields) == 1
    assert isinstance(F2.fields["email"], IntegerField)


def test_inheritance_keeps_the_fields_and_nested_populated():
    assert InheritMyNestedFilter.fields == MyNestedFilter.fields
    assert InheritMyNestedFilter.nested == MyNestedFilter.nested


def test_equals_operator():
    user = UserFactory(first_name="First Name")
    UserFactory(first_name="First Name 2")
    filter_obj = EqualFilter(data={"first_name": "First Name"})
    result = filter_obj.apply().all()
    assert len(result) == 1
    assert result[0] == user


def test_starts_with_operator():
    user = UserFactory(first_name="First Name")
    UserFactory(first_name="Name 2")
    filter_obj = StartsWithFilter(data={"first_name": "First"})
    result = filter_obj.apply().all()
    assert len(result) == 1
    assert result[0] == user


def test_like_operator():
    user = UserFactory(first_name="First Name")
    user2 = UserFactory(first_name="Name 2")
    UserFactory(first_name="test")
    filter_obj = ContainsFilter(data={"first_name": "Name"})
    result = filter_obj.apply().all()
    assert len(result) == 2
    assert {u for u in result} == {user, user2}


def test_foreign_key_contains_operator():
    user = UserFactory(first_name="First Name")
    user2 = UserFactory(first_name="Name")
    a1 = ArticleFactory(user=user)
    ArticleFactory(user=user2)
    filter_obj = ContainsFKFilter(data={"author_first_name": "First"})
    result = filter_obj.apply().all()
    assert len(result) == 1
    assert result[0] == a1


def test_2_foreign_keys():
    user = UserFactory(first_name="First Name", last_name="some last name")
    user2 = UserFactory(first_name="Name", last_name="test name")
    a1 = ArticleFactory(user=user)
    a2 = ArticleFactory(user=user2)
    filter_obj = Contains2FKFilter(data={"author_first_name": "Name"})
    result = filter_obj.apply().all()
    assert len(result) == 2
    assert {result[0], result[1]} == {a1, a2}

    filter_obj = Contains2FKFilter(
        data={"author_first_name": "Name", "author_last_name": "some"}
    )
    result = filter_obj.apply().all()
    assert len(result) == 1
    assert result[0] == a1

    filter_obj = Contains2FKFilter(
        data={"author_first_name": "Name", "author_last_name": "test"},
        operator=OrOperator,
    )
    result = filter_obj.apply().all()
    assert len(result) == 2
    assert {result[0], result[1]} == {a1, a2}


def test_multiple_filters():
    user = UserFactory(first_name="First Name")
    user2 = UserFactory(last_name="Last Name")
    a1 = ArticleFactory(user=user)
    a2 = ArticleFactory(user=user2)
    filter_obj = MultipleFKFilter(
        data={"author_first_name": "Name", "author_last_name_istarts": "lasT"},
        operator=OrOperator,
    )
    result = filter_obj.apply().order_by(User.id.asc()).all()
    assert len(result) == 2
    assert result == [a1, a2]
    filter_obj = MultipleFKFilter(
        data={"author_first_name": "Name", "author_last_name_istarts": "Name"},
        operator=OrOperator,
    )
    result = filter_obj.apply().order_by(User.id.asc()).all()
    assert len(result) == 1
    assert result == [a1]


def test_filter_validation():
    f = TypedFilter(data={"min_age": "12"})
    assert not f.validated
    f.validate()
    assert f.validated
    assert f.marshmallow_schema is None


def test_filter_validation_fails():
    f = TypedFilter(data={"min_age": "a"})
    assert not f.validated
    with pytest.raises(FilterValidationError):
        f.validate()
    assert not f.validated


def test_nested_filter_validation():
    with pytest.raises(FilterValidationError) as exc:
        MyNestedFilter(
            data={
                "email": "test2.com",
                "nested1": {"min_age": "abc"},
                "nested2": {"author_last_name_istarts": "name"},
            },
            operator=OrOperator,
        ).apply()
    assert exc.value.json() == [{"min_age": "Expected to be of type int"}]


def test_nested_filter_marshmallow_validation():

    with pytest.raises(ValidationError) as exc:
        FirstNameMarshmallowFilter(
            data={
                "email": "test2.com",
                "nested2": {"author_first_name": "abc"},
            },
        ).apply()
    assert exc.value.messages == {"author_first_name": ["Must be one of: john, james."]}


def test_filter_marshmallow_validation_at_instantiation(db_session):
    class F(Filter):
        email = StringField()

        class Meta:
            model = User
            session = db_session

    class M(Schema):
        email = fields.Email(required=True)

    with pytest.raises(ValidationError) as exc:
        F(
            data={
                "email": "test2.com",
            },
            marshmallow_schema=M,
        ).apply()
    assert exc.value.messages == {"email": ["Not a valid email address."]}


def test_filter_marshmallow_validation(db_session):
    assert AgeMarshmallowFilter.marshmallow_schema is AgeSchema
    AgeMarshmallowFilter(data={}, session=db_session).apply()
    AgeMarshmallowFilter(
        data={"nested1": {"min_age": "20"}}, session=db_session
    ).apply()

    with pytest.raises(ValidationError) as exc:
        AgeMarshmallowFilter(
            data={"nested1": {"min_age": "12"}}, session=db_session
        ).apply()

    assert exc.value.messages == {"min_age": ["Must be greater than or equal to 20."]}

    with pytest.raises(ValidationError) as exc:
        AgeMarshmallowFilter(
            data={"nested1": {"min_age": "a"}}, session=db_session
        ).apply()
    assert exc.value.messages == {"min_age": ["Not a valid integer."]}


def test_typed_filter():
    user = UserFactory(
        first_name="Name",
        age=30,
        birth_date=date(1990, 1, 1),
        created_at=datetime(2021, 1, 1, tzinfo=timezone.utc),
    )
    user2 = UserFactory(
        last_name="Last Name",
        age=25,
        birth_date=date(1995, 1, 1),
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    filter_obj = TypedFilter(
        data={"first_name": "Name", "min_age": 30, "created_at": "2020-01-01"},
        operator=OrOperator,
    )
    result = filter_obj.apply().order_by(User.id.asc()).all()
    assert result == [user, user2]

    filter_obj = TypedFilter(
        data={"first_name": "Name", "min_age": 30},
        operator=OrOperator,
    )
    result = filter_obj.apply().order_by(User.id.asc()).all()
    assert result == [user]


def test_typed_filter_validation():
    filter_obj = TypedFilter(
        data={
            "min_age": "a",
            "until_birth_date": "invalid_format",
            "created_at": "2020-01-01",
        },
        operator=OrOperator,
    )
    with pytest.raises(FilterValidationError) as exc:
        filter_obj.apply()
    assert len(exc.value.field_errors) == 2
    assert exc.value.json() == [
        {"min_age": "Expected to be of type int"},
        {
            "until_birth_date": "time data 'invalid_format' does not match format '%Y-%m-%d'"
        },
    ]


def test_nested_filter_get_data_flat_true():
    data = {}
    assert (
        NestedFilter(Filter, operator=OrOperator, flat=True).get_data(Mock(data=data))
        is data
    )


def test_nested_filter_get_data_source_name():
    field = NestedFilter(Filter, operator=OrOperator)
    field.__set_name__(None, "field")
    assert field.get_data_source_name() == "field"
    field = NestedFilter(
        Filter, operator=OrOperator, data_source_name="some_source_name"
    )
    field.__set_name__(None, "field")
    assert field.get_data_source_name() == "some_source_name"


def test_nested_filter_get_data_flat_false():
    data = {}
    field = NestedFilter(Filter, operator=OrOperator, flat=False)
    field.__set_name__(None, "field")
    assert field.get_data(Mock(data=data)) is not data
    assert field.get_data(Mock(data=data)) == data


def test_nested_filter_get_data_with_data_source_name():
    assert (
        NestedFilter(
            Filter, operator=OrOperator, data_source_name="not_found"
        ).get_data(Mock(data={}))
        == {}
    )


def test_nested_filter_get_data_not_dict():
    field = NestedFilter(Filter, operator=OrOperator, flat=False)
    field.__set_name__(None, "field")
    with pytest.raises(ValueError):
        field.get_data(Mock(data={"field": 1}))


@pytest.mark.parametrize(
    "data_source_name, expected",
    [
        [None, {"k1": "v1"}],
        ["source", {"k2": "v2"}],
    ],
)
def test_nested_filter_get_data(data_source_name, expected):
    data = {"field": {"k1": "v1"}, "source": {"k2": "v2"}}
    field = NestedFilter(
        Filter,
        operator=OrOperator,
        flat=False,
        data_source_name=data_source_name,
    )
    field.__set_name__(None, "field")
    assert field.get_data(Mock(data=data)) == expected


def test_apply_nested_empty():
    field = NestedFilter(TypedFilter, operator=OrOperator)
    field.__set_name__(None, "field")
    assert field.apply(Mock(data={})).compare(empty_sql())


def test_apply_nested_filter_as_field():
    field = NestedFilter(TypedFilter, operator=OrOperator, flat=False)
    field.__set_name__(None, "field")
    result = field.apply(
        Mock(data={"field": {"first_name": "test"}}, marshmallow_schema=None)
    )
    assert compares_expressions(result, (User.first_name == "test").self_group())


def test_apply_nested_filter():
    user = UserFactory(
        last_name="Name",
        age=30,
        birth_date=date(1990, 1, 1),
        created_at=datetime(2021, 1, 1),
        email="abc@test.com",
    )
    user2 = UserFactory(
        last_name="Last Name",
        age=25,
        birth_date=date(1995, 1, 1),
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        email="abc@test2.com",
    )
    result = (
        MyNestedFilter(
            data={
                "email": "test.com",
                "nested1": {"min_age": 29},
                "nested2": {"author_last_name_istarts": "name"},
            }
        )
        .apply()
        .all()
    )
    assert result == [user]
    result = (
        MyNestedFilter(
            data={
                "email": "test2.com",
                "nested1": {"min_age": 29},
                "nested2": {"author_last_name_istarts": "name"},
            },
            operator=OrOperator,
        )
        .apply()
        .all()
    )
    assert result == [user, user2]

    list(MyNestedFilter.nested.values())[0].outer_operator = AndOperator
    result = (
        MyNestedFilter(
            data={
                "email": "test2.com",
                "nested1": {"min_age": 29},
                "nested2": {"author_last_name_istarts": "name"},
            },
            operator=OrOperator,
        )
        .apply()
        .all()
    )
    assert result == [user]


def test_filter_with_method_field(db_session):
    class MyFilter(Filter):
        test = MethodField(method="filter_first_name", data_source_name="custom_key")
        test2 = MethodField(method="filter_last_name")
        age = Field(lookup_operator=GTEOperator)

        def filter_first_name(self, value):
            return User.first_name == value

        def filter_last_name(self, value):
            return User.last_name.startswith(value)

        class Meta:
            model = User
            session = db_session

    user = UserFactory(first_name="John", last_name="Doe", age=25)
    user2 = UserFactory(first_name="John", last_name="Jack", age=20)

    assert set(MyFilter(data={"custom_key": "John"}).apply()) == {user, user2}
    assert (
        set(
            MyFilter(
                data={"custom_key": "John", "test2": "J"},
            ).apply()
        )
        == {user2}
    )
    assert set(
        MyFilter(data={"custom_key": "John", "test2": "J"}, operator=OrOperator).apply()
    ) == {user2, user}
    assert set(MyFilter(data={"test2": "J"}, operator=OrOperator).apply()) == {user2}
    assert set(
        MyFilter(data={"test2": "J", "age": 25}, operator=OrOperator).apply()
    ) == {user2, user}
