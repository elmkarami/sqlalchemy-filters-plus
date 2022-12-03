from datetime import datetime

import factory
import faker
from factory.alchemy import SQLAlchemyModelFactory

from tests.models import Article, Category, User

factories_registry = set()
Faker = faker.Faker()


class BaseModelFactory(SQLAlchemyModelFactory):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        factories_registry.add(cls)

    class Meta:
        abstract = True


class UserFactory(BaseModelFactory):
    birth_date = factory.Sequence(lambda n: datetime.strptime(Faker.date(), "%Y-%m-%d"))

    class Meta:
        model = User


class CategoryFactory(BaseModelFactory):
    class Meta:
        model = Category


class ArticleFactory(BaseModelFactory):
    category = factory.SubFactory(CategoryFactory)
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Article


def patch_factories_session(session):
    for _factory in factories_registry:
        _factory._meta.sqlalchemy_session = session
