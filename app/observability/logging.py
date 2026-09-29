"""Local structured logging configuration."""

from __future__ import annotations

import logging

from app.observability.request_context import build_log_extra


class RequestContextFormatter(logging.Formatter):
    """Render log records with an explicit request context."""

    def format(self, record: logging.LogRecord) -> str:
        extras = build_log_extra(**getattr(record, "extra_fields", {}))
        for key, value in extras.items():
            setattr(record, key, value)
        return super().format(record)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    formatter = RequestContextFormatter(
        "%(asctime)s %(levelname)s %(name)s "
        "request_id=%(request_id)s tenant_id=%(tenant_id)s "
        "org_id=%(org_id)s user_id=%(user_id)s message=%(message)s"
    )

    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)

    root_logger.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            RequestContextFormatter(
                "%(asctime)s %(levelname)s %(name)s "
                "request_id=%(request_id)s tenant_id=%(tenant_id)s "
                "org_id=%(org_id)s user_id=%(user_id)s message=%(message)s"
            )
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


__all__ = ["RequestContextFormatter", "configure_logging", "get_logger"]
