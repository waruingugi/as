import logging
import logging.config
import os
from functools import lru_cache

# Configure logging to use both Console & Better Stack
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {"format": "%(name)-12s %(levelname)-8s %(message)s"},
            "json": {
                "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "name": "%(name)s"}',
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
            },
            "logtail": {
                "class": "logtail.LogtailHandler",
                "source_token": os.environ["LOGTAIL_TOKEN"],
                "host": os.environ[
                    "LOGTAIL_HOST"
                ],  # Force the correct ingestion endpoint
                "level": logging.INFO,
                "formatter": "json",
            },
        },
        "loggers": {
            "": {
                "level": "INFO",
                "handlers": ["console", "logtail"],
            },
        },
    }
)


@lru_cache
def instantiate_logger() -> logging.Logger:
    logger_ = logging.getLogger(__name__)
    return logger_


logger = instantiate_logger()
