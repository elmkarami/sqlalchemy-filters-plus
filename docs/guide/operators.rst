Operators
---------


SQLAlchemy filters plus provides a handful operators that makes easy to filter objects in a flexible manner.
These operators define how to filter columns in the database.
Basically an operator reflects an sql operation that could be performed on a column, a value or both.


API Usage
=========

The Operator API is pretty straightforward, we can think of them as wrappers of the builtin sqlalchemy operators.

Here's an example on how we can use an Operator:

.. code-block:: python

    from sqlalchemy import column

    from sqlalchemy_filters.operators import IsOperator, BetweenOperator

    is_operator = IsOperator(sql_expression=column("my_column"), params=["value"])
    is_operator.to_sql()  # equivalent to column("my_column").is_("value")

    is_operator = BetweenOperator(sql_expression=column("age"), params=[20, 30])
    is_operator.to_sql()  # equivalent to column("age").between(20, 30)

Define custom operators
=======================

Sometimes the provided operators are not enough, hence the need of creating custom operators. Fortunately, this is
a simple process as shown bellow.

Let's say we want to have a custom operator that tries to match the end of a string in lower case

.. code-block:: python

    from sqlalchemy import func
    from sqlalchemy.sql.operators import endswith_op

    from sqlalchemy_filters.operators import BaseOperator, register_operator


    @register_operator(endswith_op)
    class MyCustomOperator(BaseOperator):

        def to_sql(self):
            return self.operator(func.lower(self.sql_expression), *map(func.lower, self.params))



Sometime there is no builtin SQLALchemy operator that can be used to make life easier for what you want to do, the good
part about :attr:`sqlalchemy_filters.operators.register_operator`, is that you don't have to register anything. Example:

.. code-block:: python

    @register_operator
    class MyCustomOperator(BaseOperator):

        def to_sql(self):
            return self.sql_expression == "ABC"


