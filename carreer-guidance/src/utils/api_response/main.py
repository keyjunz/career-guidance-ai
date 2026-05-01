import json
import logging
from typing import Any, Optional

from typing_extensions import override

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
"""
Classes for generating API responses.

Classes:
- Ok: Represents a successful API response.
- BaseException: Base class for API exceptions.
- NotFound: Represents a 404 Not Found exception.
- MethodNotAllowed: Represents a 405 Method Not Allowed exception.
- InternalServerError: Represents a 500 Internal Server Error exception.
"""


class Ok:
    def __init__(
        self,
        body,
        headers: Optional[dict[str, Any]] = None,
    ):
        if headers is None:
            headers = {"Content-Type": "application/json"}

        self.body = body
        self.headers = headers

    def get_response(self):
        # Ensure body is properly serialized to JSON
        if isinstance(self.body, dict):
            body_json = json.dumps(self.body)
        else:
            body_json = str(self.body)

        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": self.headers,
            "cookies": [],
            "body": body_json,
        }


class Redirect:
    def __init__(self, location, body=""):
        self.location = location
        self.body = body

    def get_response(self):
        return {
            "isBase64Encoded": False,
            "statusCode": 302,
            "headers": {"Location": self.location},
            "cookies": [],
            "body": json.dumps(self.body),
        }


class APIException(Exception):
    def get_response(
        self, fallback_message: str | None = "An error occurred."
    ) -> dict[str, Any]:
        return {
            "isBase64Encoded": False,
            # "statusCode": ???, # Implement this in the child classes
            "headers": {"Content-Type": "application/json"},
            "cookies": [],
            "body": json.dumps(
                {
                    "error": str(self) or fallback_message,
                }
            ),
        }


class BadRequest(APIException):
    @override
    def get_response(
        self, fallback_message: str | None = "Bad request."
    ) -> dict[str, Any]:
        response = super().get_response(fallback_message)
        response["statusCode"] = "400"
        return response


class NotFound(APIException):
    @override
    def get_response(
        self, fallback_message: str | None = "Not found."
    ) -> dict[str, Any]:
        response = super().get_response(fallback_message)
        response["statusCode"] = "404"
        return response


class MethodNotAllowed(APIException):
    @override
    def get_response(
        self, fallback_message: str | None = "Method not allowed."
    ) -> dict[str, Any]:
        response = super().get_response(fallback_message)
        response["statusCode"] = "405"
        return response


class InternalServerError(APIException):
    @override
    def get_response(
        self, fallback_message: str | None = "Internal server error."
    ) -> dict[str, Any]:
        response = super().get_response(fallback_message)
        response["statusCode"] = "500"
        return response


class TooManyRequests(APIException):
    @override
    def get_response(
        self, fallback_message: str | None = "Too many requests."
    ) -> dict[str, Any]:
        response = super().get_response(fallback_message)
        response["statusCode"] = "429"
        return response
