import logging
import os.path
import sys
from functools import lru_cache


class SourceFormatter(logging.Formatter):
    def format(self, record) -> str:
        """Modify the logger so that it pre-pends source of the log"""
        module, func = record.module, record.funcName

        path_parts: list[str] = record.pathname.split(os.sep)
        module, file_name = path_parts[-2], path_parts[-1]

        # Pr-epend the source of the log
        record.msg = f"{module}:{file_name}:{func}: {record.msg}"

        # Call the original formatter to apply any additional formatting
        return super(SourceFormatter, self).format(record)


@lru_cache
def instantiate_logger() -> logging.Logger:
    logger_ = logging.getLogger(__name__)
    logger_.setLevel(logging.INFO)

    # Set the source formatter
    formatter = SourceFormatter("[%(asctime)s] %(levelname)s - %(message)s")

    # Create a stream handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger_.addHandler(handler)

    return logger_


logger = instantiate_logger()
