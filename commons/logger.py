import logging
import logging.config
import os
from functools import lru_cache

from django.conf import settings

# Determine if we are in development mode (DEBUG=1)
DEBUG_MODE = getattr(settings, "DEBUG", False)

# Configure logging to use Console in Dev and Logtail in Production
log_handlers = ["console"]  # Default to console logging

if not DEBUG_MODE:  # Only add Logtail if not in DEBUG mode
    log_handlers.append("logtail")

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
                "source_token": os.getenv("LOGTAIL_TOKEN", ""),
                "host": os.getenv("LOGTAIL_HOST", ""),
                "level": logging.INFO,
                "formatter": "json",
            },
        },
        "loggers": {
            "": {
                "level": "INFO",
                "handlers": log_handlers,  # Dynamically apply handlers
            },
            "django": {
                "level": "INFO",
                "handlers": log_handlers,
                "propagate": False,
            },
            "celery": {  # ADD CELERY LOGGER
                "level": "INFO",
                "handlers": log_handlers,
                "propagate": True,
            },
        },
    }
)


@lru_cache
def instantiate_logger() -> logging.Logger:
    logger_ = logging.getLogger(__name__)
    return logger_


logger = instantiate_logger()
