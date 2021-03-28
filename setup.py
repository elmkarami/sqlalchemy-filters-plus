from setuptools import setup, find_packages

version = "0.0.1"


setup(
    name="sqlalchemy-filters",
    version=version,
    description="""SQLAlchemy filters made easy""",
    author="El Mehdi Karami",
    author_email="me@elmkarami.com",
    url="https://github.com/elmkarami/sqlalchemy-filters",
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    zip_safe=False,
    keywords="sqlalchemy,filter,flask,python,sql,query",
)
