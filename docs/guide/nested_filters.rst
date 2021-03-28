Nested Filters
--------------


SQLAlchemy filters plus provides a way to build very complex queries by using
:attr:`NestedFilter <sqlalchemy_filters.filters.NestedFilter>` which make use of existing filter classes
to act as Field with the ability to specify how the inner fields of that NestedFilter should be grouped and
specifying how to combine it with the other declared fields using
:attr:`AndOperator <sqlalchemy_filters.operators.AndOperator>` and
:attr:`OrOperator <sqlalchemy_filters.operators.OrOperator>`.


Let's create an complete example:

.. code-block:: python

    from sqlalchemy.fields import StringField, IntegerField, MethodField
    from sqlalchemy.filters import DateField, Filter, NestedFilter
    from sqlalchemy.operators import GTOperator, LTEOperator, ContainsOperator, AndOperator, OrOperator

    class MyFilter(Filter):
        min_age = IntegerField(field_name="age", lookup_operator=GTOperator)
        max_age = IntegerField(field_name="age", lookup_operator=LTEOperator)
        created_at = MethodField(method="filter_created_at")

        def filter_created_at(self, value):
            return User.created_at == value

        class Meta:
            model = User
            fields = ["first_name", "min_age", "max_age", "created_at"]

    class SecondFilter(Filter):
        email = StringField(lookup_operator=ContainsOperator)
        max_birth_date = DateField(field_name="birth_date", lookup_operator=LTEOperator)
        nested_data = NestedFilter(
            MyFilter,
            operator=AndOperator,  # How to join the inner fields of MyFilter (first_name, min_age)
            outer_operator=OrOperator,  # How to join the result of the NestedFilter with the
                                        # rest of SecondFilter's fields
            data_source_name="nested_data_key",  # Used to specify from where the data should be extracted
                                                 # ignored if flat is True
            flat=False  # True if MyFilter fields should be extracted at the root level,
                        # If False, then the fields data will be extracted from the key data_source_name if specified
                        # otherwise from the NestedFilter field name, in our example it's `nested_data`
        )

        class Meta:
            model = User
            session = my_session



Let's filter some objects

.. code-block:: python

    my_filter = SecondFilter(data={
        "email": "@example",
        "max_birth_date": "1980-01-01",
        "nested_data": {
            "first_name": "John",
            "min_age": 25,
            "max_age": 45,
            "created_at": "2020-01-01",
        }
    }, operator=OrOperator)
    users = my_filter.apply_all()


The result of the sql query would be similar to

.. code-block:: sql

    SELECT users.id,
           users.first_name,
           users.last_name,
           users.email,
           users.age,
           users.is_approved,
           users.birth_date,
           users.created_at,
           users.last_login_time
    FROM   users
    WHERE  ( users.created_at = '2020-01-01'
              OR users.age > 25
              OR users.age <= 45
              OR users.first_name = 'John' )
           AND ( (users.email LIKE '%' || '@example' || '%') OR users.birth_date <= '1980-01-01' )


.. note:: NestedFilter can use other NestedFilters as fields.