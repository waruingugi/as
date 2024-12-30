import logging
from functools import lru_cache

logging.config.dictConfig(  # type: ignore
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {"format": "%(name)-12s %(levelname)-8s %(message)s"}
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "console"}
        },
        "loggers": {"": {"level": "DEBUG", "handlers": ["console"]}},
    }
)


@lru_cache
def instantiate_logger() -> logging.Logger:
    logger_ = logging.getLogger(__name__)
    return logger_


logger = instantiate_logger()
