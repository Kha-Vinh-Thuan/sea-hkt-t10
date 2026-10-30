"""Business errors raised by services. main.py turns them into HTTP responses, so services never import FastAPI."""


class ServiceError(Exception):
    status_code = 400


class Forbidden(ServiceError):
    status_code = 403

class NotFound(ServiceError):
    status_code = 404


class Conflict(ServiceError):
    status_code = 409


class Invalid(ServiceError):
    status_code = 422
