![example workflow](https://github.com/elmkarami/sqlalchemy-filters-plus/actions/workflows/release.yml/badge.svg)
![example workflow](https://github.com/elmkarami/sqlalchemy-filters-plus/actions/workflows/main.yml/badge.svg)
[![codecov](https://codecov.io/gh/elmkarami/sqlalchemy-filters-plus/branch/master/graph/badge.svg?token=I7ZC1WQYEQ)](https://codecov.io/gh/elmkarami/sqlalchemy-filters-plus)

sqlalchemy-filters-plus is a light-weight extendable library for filtering queries with sqlalchemy.

Install
-

```bash
pip install sqlalchemy-filters-plus
```


Usage
-----

This library provides an easy way to filter your SQLAlchemy queries,
which can for example be used by your users as a filtering mechanism for your exposed models via an API.

Let's define an example of models that will be used as a base query.

```python
from sqlalchemy import Column, Date, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

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
```


Define your first filter
========================

Let's then define our first Filter class for the Article model

```python
from sqlalchemy_filters import Filter, StringField
from sqlalchemy_filters.operators import ContainsOperator


class ArticleFilter(Filter):
    title = StringField(lookup_operator=ContainsOperator)
    email = StringField(field_name="user.email")

    class Meta:
        model = Article
        session = my_sqlalchemy_session
```


The example above defines a new filter class attached to the Article model, we declared two fields to filter with, 
``title`` with the lookup_operator ``ContainsOperator`` and an ``email`` field which points to the user's email, hence the `field_name="user.email"` without any lookup_operator (default value is ``EqualsOperator``) that will be used to filter with on the database level. We will see other operators that can also be used.

To apply the filter class, we instantiate it and pass it the data(as a dictionary) to filter with.

```python
my_filter = ArticleFilter(data={"email": "some@email.com", "title": "python"})
query = my_filter.apply()  # query is a SQLAlchemy Query object
```
    




Please read the full documentation here https://sqlalchemy-filters-plus.readthedocs.io/


