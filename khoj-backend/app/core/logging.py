import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_id: ContextVar[str] = ContextVar("request_id", default="")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Allowlisted fields only; exception strings and arbitrary extras can contain PII.
        return json.dumps(
            {
                "at": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "event": record.getMessage(),
                "request_id": request_id.get(),
            }
        )


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("khoj")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for name in ("httpx", "httpcore", "sqlalchemy.engine", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)
