import pathlib

from setuptools import find_packages, setup

HERE = pathlib.Path(__file__).parent

version = "1.1.5"


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
    license="BSD",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.6",
)
