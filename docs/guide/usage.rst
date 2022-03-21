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

Fields can also refer to columns in related models (Foreign keys), let's extend our models to include a new one: Category.

Category will have a one-to-many relationship with the Article

.. code-block:: python

    class Category(Base):
        __tablename__ = "categories"
        id = Column(Integer, primary_key=True)
        name = Column(String)


    class Article(Base):
        ...
        category_id = Column(Integer, ForeignKey(Category.id), nullable=False)
        category = relationship(
            Category,
            uselist=False,
            lazy="select",
            foreign_keys=[category_id],
            backref=backref("articles", uselist=True, lazy="select"),
        )

we can now create a new filter that makes use of these relationships in a very simple way(especially when dealing with joins).

Let's take this example: Ability to filter authors by category name and by article title


.. code-block:: python

    from sqlalchemy_filters import Filter, StringField
    from sqlalchemy_filters.operators import EqualsOperator, IStartsWithOperator, IContainsOperator


    class AuthorFilter(Filter):
        title = StringField(
            field_name="articles.title", lookup_operator=IContainsOperator
        )
        category = StringField(
            field_name="articles.category.name", lookup_operator=IContainsOperator
        )

        class Meta:
            model = User
            session = my_sqlalchemy_session


.. warning:: Trying to inherit from a filter that has a different model class will raise a :attr:`OrderByException <sqlalchemy_filters.exceptions.OrderByException>` FilterNotCompatible.

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


Paginating results
==================

Giving users the ability to paginate through results matching some filters is mandatory in every modern application.

To paginate result, you should add a `page_size` attribute to the class `Meta` of the filter or pass it as part of the data at the instantiation level.
Calling the :attr:`paginate <sqlalchemy_filters.filters.BaseFilter.paginate>` on a filter object will return a :attr:`Paginator <sqlalchemy_filters.paginator.Paginator>` object,
this object should do all the heavy lifting of slicing and paginating through objects from the database.

Here is an example of how can the paginator be generated:

.. code-block:: python

    class MyFilter(Filter):
        first_name = StringField()

        class Meta:
            model = User
            page_size = 10
    # Or
    >>> data = {
        #...
        "page_size": 20
    }
    # Note that we did not specify which page to get, by default it will return the first page
    >>> paginator = MyFilter(data=data).paginate()
    >>> paginator.page
    1
    # We can specify the exact page we want by passing it as part of the data
    >>> data["page"] = 2
    >>> paginator = MyFilter(data=data).paginate()
    >>> paginator.page
    2
    # The paginator object has plenty of methods to make your life easier
    >>> paginator.has_next_page()
    True
    >>> paginator.has_previous_page()
    True
    # how many pages should we expect given that the total object matching query and the page_size parameter
    >>> paginator.num_pages
    5
    # How many objects match the query
    >>> paginator.count
    95
    >>> next_paginator = paginator.next_page()
    >>> next_paginator.page
    3
    >>> previous_paginator = next_paginator.previous_page()
    >>> previous_paginator.to_json()
    {
        "count": 95,
        "page_size": 20,
        "page": 2,
        "num_pages": 5,
        "has_next_page": True,
        "has_prev_page": True,
    }
    # Will return the objects matching the page of the paginator
    >>> users = paginator.get_objects()
    # Will return the sliced query using `limit` and `offset` accordingly
    >>> query = paginator.get_sliced_query()


Ordering results
================

`sqlalchemy-filters-plus` gives you the possibility to filter the queries by one or multiple fields.

You can either specify a fixed number of fields to order by or override this behavior at instantiation level.

To tell `sqlalchemy-filters-plus` how to order you results, add a `order_by` attribute in the `Meta` class, this attribute accepts multiple formats:

1. Specify directly the field you want to order by (using the `SQLAlchemy way`)

.. code-block:: python

    class MyFilter(Filter):
        first_name = StringField()

        class Meta:
            model = User
            order_by = User.first_name.asc()

    # Or as a list

    class MyFilter(Filter):
        first_name = StringField()

        class Meta:
            model = User
            order_by = [User.first_name.asc(), User.last_name.desc()]

2. Specify the field(s) as a string or as a list of strings, `sqlalchemy-filters-plus` will evaluate the string to decide which ordering should be applied.
Prefix the field name with a ``-`` (minus) to apply descending order or omit it for ascending.

.. code-block:: python

    class MyFilter(Filter):
        first_name = StringField()

        class Meta:
            model = User
            order_by = "first_name" # ascending
            # Or as a list
            # First name ascending, while last_name descending
            order_by =  ["first_name", "-last_name"]
            # or Multiple fields as a single string
            # The space between fields will be ignored, but recommended for readability
            order_by =  "first_name, -last_name"


Notice that the last option enables us to use it as an ordering mechanism for an API, giving users the ability to order by any field

.. code-block:: python

    >>> MyFilter(data={"order_by": "first_name, -last_name"})
    >>> MyFilter(data={"order_by": ["first_name", "-last_name"]})
    >>> MyFilter(data={"order_by": "first_name"})
    >>> MyFilter(data={"order_by": User.first_name.asc()})
    >>> MyFilter(data={"order_by": [User.first_name.asc(), User.last_name.desc()]})

.. warning::
    Specifying a field that does not belong to the model class will raise an :attr:`OrderByException <sqlalchemy_filters.exceptions.OrderByException>` exception.
