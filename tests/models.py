from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    age = Column(Integer)
    is_approved = Column(Boolean)
    birth_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    last_login_time = Column(Time)

    def __repr__(self):
        return "<User(first_name='%s', last_name='%s', email='%s', age='%s')>" % (
            self.first_name,
            self.last_name,
            self.email,
            self.age,
        )


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    body = Column(String)
    category_id = Column(Integer, ForeignKey(Category.id), nullable=False)
    category = relationship(
        Category,
        uselist=False,
        lazy="select",
        foreign_keys=[category_id],
        backref=backref("articles", uselist=True, lazy="select"),
    )
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    user = relationship(
        User,
        uselist=False,
        lazy="select",
        backref=backref("articles", uselist=True, lazy="select"),
    )
