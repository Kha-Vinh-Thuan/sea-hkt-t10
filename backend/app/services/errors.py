"""Business errors raised by services. main.py turns them into HTTP responses, so services never import FastAPI."""

from typing import TypeVar

from sqlmodel import Session, SQLModel

Model = TypeVar("Model", bound=SQLModel)


class ServiceError(Exception):
    status_code = 400


class NotFound(ServiceError):
    status_code = 404


class Conflict(ServiceError):
    status_code = 409


class Invalid(ServiceError):
    status_code = 422


def fetch(session: Session, model: type[Model], record_id: int) -> Model:
    record = session.get(model, record_id)
    if not record:
        raise NotFound(f"{model.__name__} not found")
    return record
