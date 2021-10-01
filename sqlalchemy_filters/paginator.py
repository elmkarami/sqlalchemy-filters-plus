import math


class Paginator:
    """
    Utility class to help paginate through results of a SQLAlchemy query.

    This is a 1-based index, meaning page=1 is the first page.
    """

    def __init__(self, query, page: int, page_size: int):
        self.query = query
        self.count = query.count()
        self.page_size = page_size or self.count
        self.page = (page or 1) if self.page_size != self.count else 1
        self.num_pages = math.ceil(self.count / self.page_size) if self.page_size else 1

    def has_next_page(self):
        """
        :return: True if the current has is not the last page .
        """
        return self.num_pages > self.page

    def has_previous_page(self):
        """
        :return: True if the current has is not the first page .
        """
        return 1 < self.page

    def next_page(self):
        """
        If this current paginator is the last page, then this method will return the current one.

        :return: Paginator object
        """
        if self.has_next_page():
            return Paginator(
                query=self.query, page=self.page + 1, page_size=self.page_size
            )
        return self

    def previous_page(self):
        """
        If this current paginator is the first page, then this method will return the current one.

        :return: Paginator object
        """
        if self.has_previous_page():
            return Paginator(
                query=self.query, page=self.page - 1, page_size=self.page_size
            )
        return self

    def get_objects(self):
        """
        :return: Evaluates the query and returns the objects from the database.
        """
        return self.get_sliced_query().all()

    def get_sliced_query(self):
        """
        :return: Can be used to get the sliced version of the query without evaluating it
        """
        return self.query.limit(self.page_size).offset((self.page - 1) * self.page_size)

    def to_json(self):
        """
        :return: dictionary containing useful data in case of paginating through an API.

        Example:

        >>> paginator.to_json()
        {
            "count": 111,
            "page_size": 10,
            "page": 2,
            "num_pages": 12,
            "has_next_page": True,
            "has_prev_page": True,
        }
        """
        return {
            "count": self.count,
            "page_size": self.page_size,
            "page": self.page,
            "num_pages": self.num_pages,
            "has_next_page": self.has_next_page(),
            "has_prev_page": self.has_previous_page(),
        }
