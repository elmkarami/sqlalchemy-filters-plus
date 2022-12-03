import logging

logger = logging.getLogger(__name__)

try:
    import sqlalchemy

    print("imported successfully")
except Exception as exc:
    logger.exception(f"error while importing SQLAlchemy: {exc}")
