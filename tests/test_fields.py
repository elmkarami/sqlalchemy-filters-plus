from datetime import date
from datetime import datetime
from unittest.mock import call
from unittest.mock import Mock

import pytest

from sqlalchemy import column

from sqlalchemy_filters import BooleanField
from sqlalchemy_filters import DateField
from sqlalchemy_filters import DateTimeField
from sqlalchemy_filters import DecimalField
from sqlalchemy_filters import exceptions
from sqlalchemy_filters import Field
from sqlalchemy_filters import FloatField
from sqlalchemy_filters import IntegerField
from sqlalchemy_filters import MethodField
from sqlalchemy_filters import StringField
from sqlalchemy_filters.exceptions import FieldValidationError
from sqlalchemy_filters.utils import empty_sql
from tests.models import Article
from tests.models import User
from tests.utils import compares_expressions


def test_field_apply_does_not_exist_in_data():
    field = Field()
    field.__set_name__(None, "name")
    assert field.apply_filter(Mock(validated_data={})).compare(empty_sql())


@pytest.mark.parametrize("allow_none", [True, False])
def test_field_allow_none_apply_does_not_exist_in_data(allow_none):
    filter_obj = Mock(validated_data={})
    field = Field(allow_none=allow_none)
    field.__set_name__(None, "name")
    field._apply_filter = Mock()
    field.apply_filter(filter_obj)
    field._apply_filter.assert_not_called()


def test_field_allow_none_false_apply_exists():
    filter_obj = Mock(validated_data={"name": None})
    field = Field(allow_none=False)
    field.__set_name__(None, "name")
    field._apply_filter = Mock()
    field.apply_filter(filter_obj)
    field._apply_filter.assert_not_called()


def test_field_allow_none_true_apply_exists():
    filter_obj = Mock(validated_data={"name": None})
    field = Field(allow_none=True)
    field.__set_name__(None, "name")
    field._apply_filter = Mock()
    field.apply_filter(filter_obj)
    field._apply_filter.assert_called_once_with(filter_obj, None)


def test_field_apply_with_default_lookup_operator():
    field = Field()
    field.__set_name__(None, "first_name")
    parent_filter = Mock(validated_data={"first_name": "test"}, Meta=Mock(model=User))
    field.post_init(parent_filter)
    assert compares_expressions(
        field.apply_filter(parent_filter), User.first_name == "test"
    )


def test_field_apply_with_field_name_default_lookup_operator():
    field = Field(field_name="first_name")
    field.__set_name__(None, "name")
    parent_filter = Mock(validated_data={"first_name": "test"}, Meta=Mock(model=User))
    field.post_init(parent_filter)
    assert compares_expressions(
        field.apply_filter(Mock(validated_data={"name": "test"})),
        User.first_name == "test",
    )


def test_define_field_for_foreign_model_column():
    field = Field(field_name="model.column")
    assert field.is_foreign_key is True


def test_define_field_set_foreign_key_dept_greater_than_one():
    with pytest.raises(ValueError) as exc:
        Field(field_name="model.other_model.column")
    assert str(exc.value) == "Dept greater than 2 not supported yet."


def test_resolve_foreign_key_as_property_argument():
    field = Field(field_name="user.email")
    parent_filter = Mock(Meta=Mock(model=Article))
    field.parent_filter = parent_filter
    field.resolve_fk()
    assert field._column is User.email
    assert field.foreign_model is User


def test_set_column():
    field = Field()
    mocked_column = Mock()
    field._column = mocked_column
    field.__set_name__(None, "name")
    assert field._column is mocked_column


def test_set_column_with_custom_column():
    mocked_column = Mock()
    field = Field(custom_column=mocked_column)
    field.__set_name__(None, "name")

    assert field._column is mocked_column


def test_set_column_with_custom_column_as_str():
    field = Field(custom_column="my_column")
    field.__set_name__(None, "name")
    field._set_column()
    assert isinstance(field._column, column("a").__class__)
    assert str(field._column) == "my_column"


def test_resolve_fk_is_not_called():
    field = Field()
    field.__set_name__(None, "name")
    field.resolve_fk = Mock()
    parent_filter = Mock()
    field.post_init(parent_filter)
    assert field.parent_filter is parent_filter
    assert field.resolve_fk.call_count == 0


def test_resolve_fk_is_called():
    field = Field()
    field.__set_name__(None, "name")
    field.is_foreign_key = True
    field.resolve_fk = Mock()
    parent_filter = Mock()
    field.post_init(parent_filter)
    assert field.parent_filter is parent_filter
    assert field.resolve_fk.call_args_list == [call()]


def test_field_apply_with_method_as_string_gets_called():
    field = MethodField(method="test")
    field.__set_name__(None, "name")
    filter_obj = Mock(data={"name": "test"}, query=Mock())
    assert isinstance(field.apply_filter(filter_obj), Mock)
    assert filter_obj.test.call_args_list == [call("test")]


def test_field_apply_with_method_gets_called():
    mocked = Mock()
    field = MethodField(method=mocked.func)
    field.__set_name__(None, "name")
    filter_obj = Mock(data={"name": "test"}, query=Mock())
    assert isinstance(field.apply_filter(filter_obj), Mock)
    assert mocked.func.call_args_list == [call("test")]


def test_field_apply_with_method_not_found():
    field = MethodField(method="not_found")
    field.__set_name__(None, "name")
    filter_obj = Mock(validated_data={"name": "test"}, query=Mock(), not_found=None)
    with pytest.raises(AttributeError) as exc:
        assert isinstance(field.apply_filter(filter_obj), Mock)
    assert str(exc.value) == "Mock has not method not_found"


def test_field_apply_with_method_not_callable():
    field = MethodField(method="not_found")
    field.__set_name__(None, "name")
    filter_obj = Mock(
        validated_data={"name": "test"}, query=Mock(), not_found="not_callable"
    )
    with pytest.raises(exceptions.FieldMethodNotFound) as exc:
        assert isinstance(field.apply_filter(filter_obj), Mock)
    assert exc.value.field_name == "name"
    assert exc.value.parent_filter is type(filter_obj)
    assert exc.value.method_name == "not_found"


def test_field_apply_method_returns_none():
    field = MethodField(method="not_found")
    field.__set_name__(None, "name")
    filter_obj = Mock(
        data={"name": "test"}, query=Mock(), not_found=Mock(return_value=None)
    )
    with pytest.raises(ValueError) as exc:
        assert isinstance(field.apply_filter(filter_obj), Mock)
    assert str(exc.value) == "Mock.not_found must return a sql expression."
    assert filter_obj.not_found.call_args_list == [call("test")]


@pytest.mark.parametrize(
    "field_class, values",
    [
        [
            IntegerField(),
            [
                "",
                "1.0",
                "1.",
                "somes tring",
                None,
            ],
        ],
        [
            DecimalField(),
            ["", "a", None],
        ],
        [
            FloatField(),
            ["", "a", None],
        ],
        [
            DateField(date_format="%Y/%m/%d"),
            ["1234/123/123", "1/2/4", "", "somes tring", 1, 1.0],
        ],
        [
            DateField(date_format="abc"),
            ["2020/12/12"],
        ],
        [
            DateField(is_timestamp=True),
            ["1234/123/123", "1/2/4", "", "somes tring", None],
        ],
        [
            DateTimeField(datetime_format="%Y/%m/%d"),
            ["1234/123/123", "1/2/4", "", "somes tring", 1, 1.0],
        ],
        [
            DateTimeField(datetime_format="abc"),
            ["2020/12/12"],
        ],
        [
            DateTimeField(is_timestamp=True),
            ["1234/123/123", "1/2/4", "", "somes tring", None],
        ],
    ],
)
def test_field_error_validation(field_class: Field, values):
    for value in values:
        with pytest.raises(FieldValidationError):
            field_class.validate(value)


@pytest.mark.parametrize(
    "field_class, values",
    [
        [
            IntegerField(),
            [
                (1, 1),
                (1.0, 1),
                (1.0, 1),
                (1.1, 1),
                ("1", 1),
                (False, 0),
                (True, 1),
            ],
        ],
        [
            DecimalField(),
            [
                (1, 1),
                (1.0, 1),
                (1.0, 1),
                (1.1, 1.1),
                ("1", 1),
                (False, 0),
                (True, 1),
            ],
        ],
        [
            FloatField(),
            [
                (1, 1),
                (1.0, 1),
                (1.0, 1),
                (1.1, 1.1),
                ("1", 1),
                (False, 0),
                (True, 1),
            ],
        ],
        [
            StringField(),
            [
                (1, "1"),
                (1.0, "1.0"),
                (1.0, "1.0"),
                (1.1, "1.1"),
                ("1", "1"),
                (False, "False"),
                (True, "True"),
                ("a", "a"),
            ],
        ],
        [
            BooleanField(),
            [
                (0, False),
                (1, True),
                (1.0, True),
                (1.0, True),
                (1.1, True),
                ("1", True),
                (False, False),
                (True, True),
                (None, False),
                ("a", True),
            ],
        ],
        [
            DateField(is_timestamp=True),
            [
                ("1579734000.0", date(2020, 1, 23)),
                (1579734000.0, date(2020, 1, 23)),
                (1579734000, date(2020, 1, 23)),
            ],
        ],
        [
            DateTimeField(is_timestamp=True),
            [
                ("1579778662.0", datetime(2020, 1, 23, 12, 24, 22)),
                (1579778662.0, datetime(2020, 1, 23, 12, 24, 22)),
                (1579778662, datetime(2020, 1, 23, 12, 24, 22)),
            ],
        ],
        [
            DateField(date_format="%Y/%m/%d"),
            [
                ("2020/01/23", date(2020, 1, 23)),
                ("2020/01/02", date(2020, 1, 2)),
            ],
        ],
        [
            DateTimeField(datetime_format="%Y/%m/%d"),
            [
                ("2020/01/23", datetime(2020, 1, 23)),
                ("2020/01/02", datetime(2020, 1, 2)),
                (datetime(2020, 12, 2), datetime(2020, 12, 2)),
                (date(2020, 12, 2), datetime(2020, 12, 2)),
            ],
        ],
        [
            DateTimeField(datetime_format="%Y/%m/%d %H:%M:%S"),
            [
                ("2020/01/23 12:24:22", datetime(2020, 1, 23, 12, 24, 22)),
                ("2020/01/02 00:00:00", datetime(2020, 1, 2)),
                (datetime(2020, 12, 2), datetime(2020, 12, 2)),
                (date(2020, 12, 2), datetime(2020, 12, 2)),
            ],
        ],
    ],
)
def test_field_validation(field_class: Field, values):
    for value, expected in values:
        assert field_class.validate(value) == expected
