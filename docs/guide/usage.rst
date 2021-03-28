Usage
-----

This library provides an easy way to filter your SQLAlchemy queries,
which can for example be used by your users as a filtering mechanism for your exposed models via an API.

Let's define an example of models that will be used as a base query.


.. code-block:: python

    from sqlalchemy import Column, Date, Integer, String
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()


    class User(Base):
        id = Column(Integer, primary_key=True)
        email = Column(String)
        age = Column(Integer)
        birth_date = Column(Date, nullable=False)


    class Article(Base):
        id = Column(Integer, primary_key=True)
        title = Column(String)
        user_id = Column(Integer, ForeignKey(User.id), nullable=False)
        user = relationship(
            User,
            uselist=False,
            lazy="select",
            backref=backref("articles", uselist=True, lazy="select"),
        )


Define your first filter
========================

Let's then define our first Filter class for the User model

.. code-block:: python

    from sqlalchemy_filters import Filter, Field
    from sqlalchemy_filters.operators import EqualsOperator


    class EmailFilter(Filter):
        email = Field(lookup_operator=EqualsOperator)

        class Meta:
            model = User
            session = my_sqlalchemy_session


The example above defines a new filter class attached to the User model, we declared one field to filter with, which is the ``email`` field and and we defined the ``lookup_operator`` (default value is ``EqualsOperator``) that will be used to filter with on the database level. We will see other operators that can also be used.

To apply the filter class, we instantiate it and pass it the data(as a dictionary) to filter with.

.. code-block:: python

    my_filter = EmailFilter(data={"email": "some@email.com"})
    query = my_filter.apply()  # query is a SQLAlchemy Query object


.. note:: Meta.session is optional, but if it's not provided at declaration time, then
    it needs to be passed at the instantiation level or replaced by a sqlalchemy ``Query``.

Example:

.. code-block:: python

    my_filter = EmailFilter(data={"email": "some@email.com"}, session=my_session)
    # or
    my_filter = EmailFilter(data={"email": "some@email.com"}, query=some_query)


Related models
++++++++++++++

Fields can also refer to columns in related models (Foreign keys)

.. code-block:: python

    from sqlalchemy_filters import Filter, StringField
    from sqlalchemy_filters.operators import EqualsOperator, StartsWithOperator


    class ArticleFilter(Filter):
        author_first_name = StringField(
            field_name="user.first_name", lookup_operator=ContainsOperator
        )
        title = StringField(lookup_operator=StartsWithOperator)

    class Meta:
        model = Article
        session = my_sqlalchemy_session


.. warning:: Filtering with depth level greater than 1 is not supported at the moment.

Declaring fields
================

Declaring fields is generally used to specify the attributes will be used to query the database, but it can get far more complex that just that. With SQLAlchemy filters plus you can define fields by using either one of these two methods or combining them:

    1. Define each attribute using the Field class as we described in the example above.
    2. Set the ``fields`` attributes on the metadata to indicate the fields that you can filter with


The first method gives you most flexibility using pre-defined or custom operators while the other one only works with the ``EqualOperator``

These two block defines exactly the same filter

.. code-block:: python

    class EmailFilter(Filter):
        email = Field(lookup_operator=EqualsOperator)

        class Meta:
            model = User
            session = my_sqlalchemy_session

    # EmailFilter behaves exactly the same as EmailFilter2

    class EmailFilter2(Filter):

        class Meta:
            model = User
            session = my_sqlalchemy_session
            fields = ["email"]


So if you're trying to use only the ``EqualsOperator`` you can just define them using the ``fields`` attributes on the meta class.

.. warning:: Once the fields attribute is set and not empty, it has to include the fields that were declared explicitly inside the filter class, otherwise they will be ignored.


.. code-block:: python

    from sqlalchemy_filters.operators import StartsWithOperator

    class MyFilter(Filter):
        email = Field(lookup_operator=StartsWithOperator)

        class Meta:
            model = User
            session = my_sqlalchemy_session
            fields = ["age", "email"]


For fields that were not explicitly declared, SQLAlchemy filters plus will try to match the appropriate Field type for it, in this example ``age`` will be of type ``sqlalchemy_filters.IntegerField``.


Field options
=============

* ``field_name``: The attribute name of the fields must not necessarily be the name of the Model attribute, as long as we override the Field's ``field_name``. Example:

.. code-block:: python


    class MyFilter(Filter):
        # Note that the filter class will look for `email_address` inside the provided data
        email_address = Field(field_name="email")

.. warning:: If none of the attribute name/field name is found on the Model, an ``AttributeError`` will be thrown.

* ``lookup_operator``: (default: :attr:`EqualsOperator <sqlalchemy_filters.operators.EqualsOperator>`) Accepts an operator class used to specify how to perform the lookup operation on the database level.

* ``custom_column``: Used to filter explicitly against a custom column, it can accept a ``str``, ``column`` object or a model attribute as shown below:

.. code-block:: python

    class MyFilter(Filter):
        email_address = Field(custom_column="email")
        user_age = Field(custom_column=column("age"))
        user_birth_date = Field(custom_column=User.birth_date)

* ``data_source_name`` defines the key used to look for the field's value inside the data dictionary.

.. code-block:: python

    class MyFilter(Filter):
        email = Field(data_source_name="email_address")

    ...

    f = MyFilter(data={"email_address": "some@email.com"})

* ``allow_none`` (default to ``False``): allow filtering with None values. Only if the data contains the value `None`:

.. code-block:: python

    class MyFilter(Filter):
        email = Field(allow_none=True)

    ...
    # Will filter by "email is None" in the database level
    MyFilter(data={"email": None}).apply()
    # No filtering will be applied to the database
    MyFilter(data={}).apply()

.. note::
    When `allow_none` is switched off, sending None values will be ignored.


Method fields
=============

:attr:`MethodField <sqlalchemy_filters.fields.MethodField>` is a field that delegates the filtering part of a specific
field to a Filter method or a custom function.

.. code-block:: python

    from sqlalchemy import func
    from sqlalchemy_filters.fields import MethodField

    def filter_first_name(value):
        # sanitize value and filter with first_name column
        return func.lower(User.first_name) == value.lower()

    class MyFilter(Filter):
        email = MethodField("get_email")
        my_field = MethodField(filter_first_name, data_source_name="custom_key")

        class Meta:
            model = User

        def get_email(self, value):
            domain = value.split("@")[1]
            return User.first_name.endswith(domain)


    MyFilter(data={"email": "some@email.com", "custom_key": "John"}).apply()

The methods/functions that were used for filtering should return a sql expression that SQLAlchemy can accept as a parameter
for the ``filter`` function of a Query.

The benefit of using a object method is that you can access other values which can be useful to filter based on multiple inputs using ``self.data``.

.. note::
    MethodField can also be referenced inside `Meta.fields`.

.. warning::
    MethodFields do not validated input values. It is strongly recommended to validate the value before filtering.
