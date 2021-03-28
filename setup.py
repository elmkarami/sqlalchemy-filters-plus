import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent

version = "1.0.2"


setup(
    name="sqlalchemy-filters-plus",
    version=version,
    description="""SQLAlchemy filters made easy""",
    long_description=(HERE / "README.md").read_text(),
    long_description_content_type="text/markdown",
    author="El Mehdi Karami",
    author_email="me@elmkarami.com",
    url="https://github.com/elmkarami/sqlalchemy-filters-plus",
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    zip_safe=False,
    keywords="sqlalchemy,filter,flask,python,sql,query",
    licence="MIT",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
