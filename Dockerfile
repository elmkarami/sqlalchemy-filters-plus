FROM python:3.7-slim-buster

COPY requirements.txt ./
RUN pip install -r requirements.txt


WORKDIR /app

COPY . /app


ENTRYPOINT ["/app/entrypoint.sh"]
