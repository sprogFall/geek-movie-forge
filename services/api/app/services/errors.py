class ServiceError(Exception):
    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class NotFoundServiceError(ServiceError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail, status_code=404)


class ConflictServiceError(ServiceError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail, status_code=409)


class ValidationServiceError(ServiceError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail, status_code=422)


class UnauthorizedServiceError(ServiceError):
    def __init__(self, detail: str = "Not authenticated") -> None:
        super().__init__(detail=detail, status_code=401)


class UpstreamServiceError(ServiceError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail, status_code=502)
