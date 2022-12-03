import pytest

from sqlalchemy_filters.paginator import Paginator
from tests.factories import UserFactory
from tests.models import User


class TestPaginator:
    @pytest.fixture(autouse=True)
    def setup_query(self, db_session):
        self.users = UserFactory.create_batch(size=7)
        self.query = db_session.query(User).order_by(User.id.asc())

    def test_paginator(self):
        paginator = Paginator(query=self.query, page=1, page_size=2)
        assert not paginator.has_previous_page()
        assert paginator.has_next_page()
        assert paginator.num_pages == 4
        assert paginator.count == 7

    def test_to_json(self):
        paginator = Paginator(query=self.query, page=1, page_size=2)
        assert paginator.to_json() == {
            "count": 7,
            "page_size": 2,
            "page": 1,
            "num_pages": 4,
            "has_next_page": True,
            "has_prev_page": False,
        }
        paginator = Paginator(query=self.query, page=2, page_size=2)
        assert paginator.to_json() == {
            "count": 7,
            "page_size": 2,
            "page": 2,
            "num_pages": 4,
            "has_next_page": True,
            "has_prev_page": True,
        }
        paginator = Paginator(query=self.query, page=4, page_size=2)
        assert paginator.to_json() == {
            "count": 7,
            "page_size": 2,
            "page": 4,
            "num_pages": 4,
            "has_next_page": False,
            "has_prev_page": True,
        }

    def test_has_next_page(self):
        paginator = Paginator(query=self.query, page=1, page_size=2)
        assert paginator.has_next_page()
        paginator = Paginator(query=self.query, page=4, page_size=2)
        assert not paginator.has_next_page()

    def test_has_prev_page(self):
        paginator = Paginator(query=self.query, page=1, page_size=2)
        assert not paginator.has_previous_page()
        paginator = Paginator(query=self.query, page=4, page_size=2)
        assert paginator.has_previous_page()

    def test_get_next_page(self):
        paginator = Paginator(query=self.query, page=1, page_size=2)
        next_paginator = paginator.next_page()
        assert next_paginator.page == 2

    def test_get_next_page_on_last_page(self):
        paginator = Paginator(query=self.query, page=4, page_size=2)
        next_paginator = paginator.next_page()
        assert next_paginator is paginator

    def test_get_previous_page(self):
        paginator = Paginator(query=self.query, page=2, page_size=2)
        next_paginator = paginator.previous_page()
        assert next_paginator.page == 1

    def test_get_previous_page_on_first_page(self):
        paginator = Paginator(query=self.query, page=1, page_size=2)
        next_paginator = paginator.previous_page()
        assert next_paginator is next_paginator

    def test_get_sliced_query(self):
        paginator = Paginator(query=self.query, page=2, page_size=2)
        query = paginator.get_sliced_query()
        assert query.all() == self.users[2:4]
        paginator = Paginator(query=self.query, page=5, page_size=2)
        query = paginator.get_sliced_query()
        assert query.all() == []

    def test_get_objects(self):
        paginator = Paginator(query=self.query, page=2, page_size=2)
        assert paginator.get_objects() == self.users[2:4]
        paginator = Paginator(query=self.query, page=5, page_size=2)
        assert paginator.get_objects() == []

    def test_unlimited_size(self):
        paginator = Paginator(query=self.query, page=2, page_size=0)
        assert paginator.page == 1
        assert paginator.page_size == 7
        assert paginator.num_pages == 1
        assert paginator.get_objects() == self.users
        assert not paginator.has_next_page()
        assert not paginator.has_previous_page()
        assert paginator.next_page() is paginator
        assert paginator.previous_page() is paginator
        assert paginator.to_json() == {
            "count": 7,
            "page_size": 7,
            "page": 1,
            "num_pages": 1,
            "has_next_page": False,
            "has_prev_page": False,
        }
        assert paginator.get_objects() == self.users
        assert paginator.get_sliced_query().all() == self.users
