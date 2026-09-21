from fastapi import HTTPException, status

from src.config.loggers import Logger

logger = Logger(name=__name__)


class APIException(HTTPException):
    """
    Base exception class for API errors.

    Extends FastAPI's HTTPException with logging capabilities and
    predefined status code messages.

    Attributes:
        STATUS_CODE (dict): Mapping of HTTP status codes to error messages.
    """

    STATUS_CODE = {
        status.HTTP_400_BAD_REQUEST: "Bad request",
        status.HTTP_401_UNAUTHORIZED: "Unauthorized access",
        status.HTTP_403_FORBIDDEN: "Forbidden action",
        status.HTTP_404_NOT_FOUND: "Resource not found",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal server error",
        status.HTTP_408_REQUEST_TIMEOUT: "Request timeout",
        status.HTTP_406_NOT_ACCEPTABLE: "Not acceptable",
        status.HTTP_409_CONFLICT: "Conflict",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Unprocessable entity",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal server error",
        status.HTTP_503_SERVICE_UNAVAILABLE: "Service unavailable",
        status.HTTP_504_GATEWAY_TIMEOUT: "Gateway timeout",
        status.HTTP_505_HTTP_VERSION_NOT_SUPPORTED: "HTTP version not supported",
        status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED: "Network authentication required",
        "default": "Something went wrong",
    }

    def __init__(self, status_code: int, detail: str, *args, **kwargs):
        self.status_code = status_code
        self.detail = detail

        logger.exception(f"{self.STATUS_CODE.get(self.status_code, 'default')}: {self.detail}")

        super().__init__(status_code=self.status_code, detail=self.detail)


class NotFoundException(APIException):
    """
    Exception raised when a requested resource is not found.

    Returns HTTP 404 status code.

    Args:
        detail (str): Specific error message. Defaults to "Resource not found".
    """

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail)


class UnAuthorizedException(APIException):
    """
    Exception raised for authentication failures.

    Returns HTTP 401 status code.

    Args:
        detail (str): Specific error message. Defaults to "Unauthorized access".
    """

    def __init__(self, detail: str = "Unauthorized access"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail)


class BadRequestException(APIException):
    """
    Exception raised for invalid request data.

    Returns HTTP 400 status code.

    Args:
        detail (str): Specific error message. Defaults to "Bad request".
    """

    def __init__(self, detail: str = "Bad request"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)


class ForbiddenException(APIException):
    """
    Exception raised when user lacks permission for an action.

    Returns HTTP 403 status code.

    Args:
        detail (str): Specific error message. Defaults to "Forbidden action".
    """

    def __init__(self, detail: str = "Forbidden action"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)


class InternalServerException(APIException):
    """
    Exception raised for internal server errors.

    Returns HTTP 500 status code.

    Args:
        detail (str): Specific error message. Defaults to "Internal server error".
    """

    def __init__(self, detail: str = "Internal server error"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)


class NotAcceptableException(APIException):
    """
    Exception raised when request format is not acceptable.

    Returns HTTP 406 status code.

    Args:
        detail (str): Specific error message. Defaults to "Not acceptable".
    """

    def __init__(self, detail: str = "Not acceptable"):
        super().__init__(status.HTTP_406_NOT_ACCEPTABLE, detail)
