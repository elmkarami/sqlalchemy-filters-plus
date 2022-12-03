#!/bin/bash


 result=$(python -c "import sqlalchemy")
if [ $? -eq 0 ]; then
     pytest --cov=sqlalchemy_filters --cov-report=xml
else
  echo "sqlalchemy could not be imported..skipping tests"
fi
