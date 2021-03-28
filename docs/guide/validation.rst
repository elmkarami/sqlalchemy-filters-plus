Validation
----------

Validating inputs at the filters/fields level is crucial to be in accordance of what the database expects and prevent unexpected errors.

SQLAlchemy filters plus provides multiple level of validations.


How it works
============

Field validation is ensuring that a specific field value is what we expect it to be. There are multiple field types that
are predefined and can be used to validate the desired fields.

Let's see an example of how we can apply that into our example:

.. code-block:: python

    from sqlalchemy_filters import Filter, DateField


    class MyFilter(Filter):
        birth_date = DateField()  # can take a format parameter, default is "%Y-%m-%d"

        class Meta:
            model = User
            session = my_session


The above defines a filter with a single :attr:`DateField <sqlalchemy_filters.fields.DateField>` field. This will ensure
that the passed value is a `datetime` value or can be parsed as a `datetime`.
Otherwise a :attr:`FilterValidationError <sqlalchemy_filters.exceptions.FilterValidationError>` exception will be thrown.


.. code-block:: python

    >>> from sqlalchemy_filters.exceptions import FilterValidationError
    >>> try:
    >>>     MyFilter(data={"birth_date": "abc"}).apply()
    >>> except FilterValidationError as exc:
    >>>     print(exc.json())
    [
        {"birth_date": "time data 'abc' does not match format '%Y-%m-%d'"}
    ]


This exception encapsulates all the field errors that were encountered, it also provides a
:meth:`json()<sqlalchemy_filters.exceptions.FilterValidationError.json>` method to make it human readable which gives
the possibility of returning it as a response in a REST API.

It's also a wrapper around the :attr:`FieldValidationError <sqlalchemy_filters.exceptions.FieldValidationError>`
exception, you can get the full list of wrapped exceptions
by accessing to :attr:`fields_errors <sqlalchemy_filters.exceptions.FilterValidationError.field_errors>` attribute

.. code-block:: python

    >>> exc.field_errors


Custom Schema Validation
========================

SQLAlchemy filters plus support custom validation with `Marhsmallow <https://marshmallow.readthedocs.io/>`_.

The Marshmallow schema will provide a validation for the whole :attr:`Filter <sqlalchemy_filters.filters.Filter>` class.

Let's define our fist Marshmallow schema

.. code-block:: python

    from marshmallow import Schema, fields, validate


    class FirstNameSchema(Schema):
        first_name = fields.String(validate=validate.OneOf(["john", "james"]), required=True)


First define a Marshmallow schema, then we can inject it into the Filter class using 2 approaches:

    1. The first one is using `Meta.marshmallow_schema` attribute:

    .. code-block:: python

        from sqlalchemy_filters import Filter, StringField


        class MyFilter(Filter):

            class Meta:
                model = User
                fields = ["first_name"]
                session = my_session
                marshmallow_schema = FirstNameSchema

        >>> MyFilter(data={"first_name": "test"}).apply()
        marshmallow.exceptions.ValidationError: {'first_name': ['Must be one of: john, james.']}

    2. Or pass it as an argument at the instantiation level of the filter class

    .. code-block:: python

        >>> MyFilter(data={"first_name": "test"}, marshmallow_schema=FirstNameSchema).apply()
        marshmallow.exceptions.ValidationError: {'first_name': ['Must be one of: john, james.']}


Define custom field and validation
==================================

Field validation is performed by the :attr:`validate <sqlalchemy_filters.fields.BaseField.validate>` method. The Filter class
calls the validate method for each defined field.

To create a custom field validation we can inherit from the :attr:`Field <sqlalchemy_filters.fields.Field>` class or any other class that inherits
from the Field class (example: StringField, DateField...) and redefine the validate method,
the return value will be used to filter the column with, or an :attr:`FieldValidationError <sqlalchemy_filters.exceptions.FieldValidationError>` exception can be raised

Example:

    .. code-block:: python

        from sqlalchemy_filters.fields import StringField
        from sqlalchemy_filters.exceptions import FieldValidationError


        class EmailField(StringField):
            def validate(self, value):
                value = super().validate(value)
                if "@mydomain.com" not in value:
                    raise FieldValidationError("Only emails from mydomain.com are allowed.")
                return value


