import logging
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Union

from pydantic import BaseModel
from pythonjsonlogger.json import JsonFormatter


class RequestContextVar(BaseModel):
    request_id: str
    request_path: str
    start_time: float | None = None


request_ctx_var: ContextVar[Union[RequestContextVar, None]] = ContextVar(
    "request_ctx_var", default=None
)

__logger: logging.Logger | None = None


class CustomJsonFormatter(JsonFormatter):
    """Custom JSON formatter for logging with additional fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        log_record["timestamp"] = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).isoformat()

        var = request_ctx_var.get()
        if var is not None:
            log_record["request_id"] = getattr(var, "request_id", None)
            log_record["request_path"] = getattr(var, "request_path", None)
            start_time = getattr(var, "start_time", None)
            if start_time is not None:
                log_record["response_time"] = (
                    f"{round((datetime.now(tz=timezone.utc).timestamp() - start_time) * 1000, 4)}ms"
                )
        else:
            log_record["request_id"] = None
            log_record["request_path"] = None
            log_record["response_time"] = None

        log_record["pathname"] = record.pathname
        log_record["line"] = record.lineno
        log_record["severity"] = record.levelname
        if record.exc_info:
            log_record["error"] = "".join(traceback.format_exception(*record.exc_info))
        super().add_fields(log_record, record, message_dict)


def get_logger() -> logging.Logger:
    """Logger factory function to create a logger with JSON formatting."""

    global __logger
    if __logger:
        return __logger

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    handler = logging.StreamHandler()
    handler.setFormatter(CustomJsonFormatter())
    logger.addHandler(handler)
    __logger = logger
    return logger
