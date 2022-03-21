from unittest.mock import Mock, patch, call
import pytest

from sqlalchemy import column
from sqlalchemy import text
from sqlalchemy import func
from sqlalchemy import not_

from sqlalchemy_filters import operators
from sqlalchemy_filters.exceptions import InvalidParamError
from tests.utils import compares_expressions


def compile_sql(expression):
    return expression.compile(compile_kwargs={"literal_binds": True})


def test_register_operator():
    op = Mock()

    @operators.register_operator(sql_operator=op)
    class F:
        pass

    assert F().operator is op


@pytest.mark.parametrize("version", ["1", "1.1", "1.2", "1.3", "1.3.22"])
def test_sa_1_4_compatible_for_older_versions(version):
    with patch.object(operators, "SQLALCHEMY_VERSION", version):
        f = Mock()
        assert operators.sa_1_4_compatible(f) is f


@pytest.mark.parametrize(
    "sql_exp, params",
    [
        [text(""), column("a").is_(None)],
        [text("1 = 1"), column("a").is_(None)],
    ],
)
def test_sa_1_4_compatible(sql_exp, params):
    with patch.object(operators, "SQLALCHEMY_VERSION", "1.4"):
        to_sql = Mock()
        self = Mock(get_sql_expression=Mock(return_value=sql_exp), params=[params])
        to_sql_v2 = operators.sa_1_4_compatible(to_sql)
        to_sql_v2(self)
        assert not to_sql.called
        assert self.operator.called_once
        param1, param2 = self.operator.call_args[0]
        assert compares_expressions(param1, params)
        assert compares_expressions(param2, sql_exp)


@pytest.mark.parametrize(
    "sql_exp, params",
    [
        [column("a").is_(None), text("")],
        [column("a").is_(None), text("1 = 1")],
    ],
)
def test_sa_1_4_compatible_should_not_alter_params(sql_exp, params):
    with patch.object(operators, "SQLALCHEMY_VERSION", "1.4"):
        to_sql = Mock()
        self = Mock(get_sql_expression=Mock(return_value=sql_exp), params=[params])
        to_sql_v2 = operators.sa_1_4_compatible(to_sql)
        to_sql_v2(self)
        assert to_sql.called
        assert not self.operator.called
        assert to_sql.call_args == call(self)


def test_operator_init():
    op = operators.BaseOperator(sql_expression="A", params=["B"])
    assert op.sql_expression == "A"
    assert op.params == ["B"]
    assert str(op.get_sql_expression()) == '"A"'


def test_equals_operator():
    _column = column("my_column")
    op = operators.EqualsOperator(sql_expression=_column, params=["A"])
    assert op.to_sql().compare(_column == "A")


def test_is_operator():
    _column = column("my_column")
    op = operators.IsOperator(sql_expression=_column, params=["A"])
    assert op.to_sql().compare(_column.is_("A"))


def test_is_not_operator():
    _column = column("my_column")
    op = operators.IsOperator(sql_expression=_column, params=["A"])
    assert op.to_sql().compare(not_(_column.is_("A")))


def test_gte_operator():
    _column = column("my_column")
    op = operators.GTEOperator(sql_expression=_column, params=["A"])
    assert op.to_sql().compare(_column >= "A")


def test_lte_operator():
    _column = column("my_column")
    op = operators.LTEOperator(sql_expression=_column, params=["A"])
    assert op.to_sql().compare(_column <= "A")


def test_starts_with_operator():
    _column = column("my_column")
    op = operators.StartsWithOperator(sql_expression=_column, params=["A"])
    assert op.to_sql().compare(_column.startswith("A"))


def test_istarts_with_operator():
    _column = column("my_column")
    op = operators.IStartsWithOperator(sql_expression=_column, params=["A"])
    expected = compile_sql(func.lower(_column).startswith(func.lower("A")))
    assert str(compile_sql(op.to_sql())) == str(expected)


def test_ends_with_operator():
    _column = column("my_column")
    op = operators.EndsWithOperator(sql_expression=_column, params=["A"])
    assert op.to_sql().compare(_column.endswith("A"))


def test_iends_with_operator():
    _column = column("my_column")
    op = operators.IEndsWithOperator(sql_expression=_column, params=["A"])
    expected = compile_sql(func.lower(_column).endswith(func.lower("A")))
    assert str(compile_sql(op.to_sql())) == str(expected)


def test_contains_operator():
    _column = column("my_column")
    op = operators.ContainsOperator(sql_expression=_column, params=["A"])
    assert op.to_sql().compare(_column.contains("A"))


@pytest.mark.parametrize("value", [[], ["A"], ["A", "B"]])
def test_in_operator(value):
    _column = column("my_column")
    op = operators.INOperator(sql_expression=_column, params=value)
    assert op.to_sql().compare(_column.in_(value))


def test_range_operator():
    _column = column("my_column")
    op = operators.RangeOperator(sql_expression=_column, params=[0, 10])
    assert op.to_sql().compare(_column.between(0, 10))


def test_in_operator_invalid_params():
    with pytest.raises(InvalidParamError) as exc:
        operators.BaseOperator(sql_expression="A", params="A")

    assert str(exc.value) == "BaseOperator.params expected to be a list, got str."


def test_range_operator_invalid_params():
    with pytest.raises(InvalidParamError) as exc:
        operators.RangeOperator(sql_expression="A", params=[])

    assert str(exc.value) == "RangeOperator.params should have exactly 2 values, got 0."


def test_icontains_operator():
    _column = column("my_column")
    op = operators.IContainsOperator(sql_expression=_column, params=["A"])
    assert compares_expressions(op.to_sql(), func.lower(_column).contains(func.lower("A")))
