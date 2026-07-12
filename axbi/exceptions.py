# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

from collections import defaultdict
from typing import Any

from flask_babel import gettext as _
from marshmallow import ValidationError

from axbi.errors import AxBIError, AxBIErrorType, ErrorLevel


class AxBIException(Exception):  # noqa: N818
    status = 500
    message = ""

    def __init__(
        self,
        message: str = "",
        exception: Exception | None = None,
        error_type: AxBIErrorType | None = None,
    ) -> None:
        if message:
            self.message = message
        self._exception = exception
        self._error_type = error_type
        super().__init__(self.message)

    @property
    def exception(self) -> Exception | None:
        return self._exception

    @property
    def error_type(self) -> AxBIErrorType | None:
        return self._error_type

    def to_dict(self) -> dict[str, Any]:
        rv = {}
        if hasattr(self, "message"):
            rv["message"] = self.message
        if self.error_type:
            rv["error_type"] = self.error_type
        if self.exception is not None and hasattr(self.exception, "to_dict"):
            rv = {**rv, **self.exception.to_dict()}
        return rv


class AxBIErrorException(AxBIException):
    """Exceptions with a single AxBIErrorType associated with them"""

    def __init__(self, error: AxBIError, status: int | None = None) -> None:
        super().__init__(error.message)
        self.error = error
        if status is not None:
            self.status = status

    def to_dict(self) -> dict[str, Any]:
        return self.error.to_dict()


class AxBIGenericErrorException(AxBIErrorException):
    """Exceptions that are too generic to have their own type"""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(
            AxBIError(
                message=message,
                error_type=AxBIErrorType.GENERIC_BACKEND_ERROR,
                level=ErrorLevel.ERROR,
            )
        )
        if status is not None:
            self.status = status


class AxBIErrorFromParamsException(AxBIErrorException):
    """Exceptions that pass in parameters to construct a AxBIError"""

    def __init__(
        self,
        error_type: AxBIErrorType,
        message: str,
        level: ErrorLevel,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            AxBIError(
                error_type=error_type, message=message, level=level, extra=extra or {}
            )
        )


class AxBIErrorsException(AxBIException):
    """Exceptions with multiple AxBIErrorType associated with them"""

    def __init__(self, errors: list[AxBIError], status: int | None = None) -> None:
        super().__init__(str(errors))
        self.errors = errors
        if status is not None:
            self.status = status


class AxBISyntaxErrorException(AxBIErrorsException):
    status = 422
    error_type = AxBIErrorType.SYNTAX_ERROR

    def __init__(self, errors: list[AxBIError]) -> None:
        super().__init__(errors)


class AxBITimeoutException(AxBIErrorFromParamsException):
    status = 408


class AxBIGenericDBErrorException(AxBIErrorFromParamsException):
    status = 400

    def __init__(
        self,
        message: str,
        level: ErrorLevel = ErrorLevel.ERROR,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            AxBIErrorType.GENERIC_DB_ENGINE_ERROR,
            message,
            level,
            extra,
        )


class AxBITemplateParamsErrorException(AxBIErrorFromParamsException):
    status = 400

    def __init__(
        self,
        message: str,
        error: AxBIErrorType,
        level: ErrorLevel = ErrorLevel.ERROR,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error,
            message,
            level,
            extra,
        )


class AxBISecurityException(AxBIErrorException):
    status = 403

    def __init__(self, error: AxBIError, payload: dict[str, Any] | None = None) -> None:
        super().__init__(error)
        self.payload = payload


class AxBIVizException(AxBIErrorsException):
    status = 400


class NoDataException(AxBIException):
    status = 400


class NullValueException(AxBIException):
    status = 400


class AxBITemplateException(AxBIException):
    status = 422


class SpatialException(AxBIException):
    pass


class CertificateException(AxBIException):
    message = _("Invalid certificate")


class DatabaseNotFound(AxBIException):
    status = 400


class MissingUserContextException(AxBIException):
    status = 422


class QueryObjectValidationError(AxBIException):
    status = 400


class AdvancedDataTypeResponseError(AxBIException):
    status = 400


class InvalidPostProcessingError(AxBIException):
    status = 400


class CacheLoadError(AxBIException):
    status = 404


class QueryClauseValidationException(AxBIException):
    status = 400


class DashboardImportException(AxBIException):
    pass


class DatasetInvalidPermissionEvaluationException(AxBIException):
    """
    When a dataset can't compute its permission name
    """


class SerializationError(AxBIException):
    pass


class InvalidPayloadFormatError(AxBIErrorException):
    status = 400

    def __init__(self, message: str = "Request payload has incorrect format"):
        error = AxBIError(
            message=message,
            error_type=AxBIErrorType.INVALID_PAYLOAD_FORMAT_ERROR,
            level=ErrorLevel.ERROR,
        )
        super().__init__(error)


class InvalidPayloadSchemaError(AxBIErrorException):
    status = 422

    def __init__(self, error: ValidationError):
        # dataclasses.asdict does not work with defaultdict, convert to dict
        # https://bugs.python.org/issue35540
        for k, v in error.messages.items():
            if isinstance(v, defaultdict):
                error.messages[k] = dict(v)
        error = AxBIError(
            message="An error happened when validating the request",
            error_type=AxBIErrorType.INVALID_PAYLOAD_SCHEMA_ERROR,
            level=ErrorLevel.ERROR,
            extra={"messages": error.messages},
        )
        super().__init__(error)


class AxBICancelQueryException(AxBIException):
    status = 422


class QueryNotFoundException(AxBIException):
    status = 404


class ColumnNotFoundException(AxBIException):
    status = 404


class AxBIMarshmallowValidationError(AxBIErrorException):
    """
    Exception to be raised for Marshmallow validation errors.
    """

    status = 422

    def __init__(self, exc: ValidationError, payload: dict[str, Any]):
        error = AxBIError(
            message=_("The schema of the submitted payload is invalid."),
            error_type=AxBIErrorType.MARSHMALLOW_ERROR,
            level=ErrorLevel.ERROR,
            extra={"messages": exc.messages, "payload": payload},
        )
        super().__init__(error)


class AxBIParseError(AxBIErrorException):
    """
    Exception to be raised when we fail to parse SQL.
    """

    status = 422

    def __init__(  # pylint: disable=too-many-arguments
        self,
        sql: str,
        engine: str | None = None,
        message: str | None = None,
        highlight: str | None = None,
        line: int | None = None,
        column: int | None = None,
    ):
        if message is None:
            parts = [_("Error parsing")]
            if highlight:
                parts.append(_(" near '%(highlight)s'", highlight=highlight))
            if line:
                parts.append(_(" at line %(line)d", line=line))
                if column:
                    parts.append(f":{column}")
            message = "".join(parts)

        error = AxBIError(
            message=message,
            error_type=AxBIErrorType.INVALID_SQL_ERROR,
            level=ErrorLevel.ERROR,
            extra={"sql": sql, "engine": engine, "line": line, "column": column},
        )
        super().__init__(error)

    def __str__(self) -> str:
        return self.error.message


class OAuth2RedirectError(AxBIErrorException):
    """
    Exception used to start OAuth2 dance for personal tokens.

    The exception requires 3 parameters:

    - The URL that starts the OAuth2 dance.
    - The UUID of the browser tab where OAuth2 started, so that the newly opened tab
      where OAuth2 happens can communicate with the original tab to inform that OAuth2
      was successful (or not).
    - The redirect URL, so that the original tab can validate that the message from the
      second tab is coming from a valid origin.

    See the `OAuth2RedirectMessage.tsx` component for more details of how this
    information is handled.
    """

    status = 403

    def __init__(self, url: str, tab_id: str, redirect_uri: str):
        super().__init__(
            AxBIError(
                message="You don't have permission to access the data.",
                error_type=AxBIErrorType.OAUTH2_REDIRECT,
                level=ErrorLevel.WARNING,
                extra={"url": url, "tab_id": tab_id, "redirect_uri": redirect_uri},
            )
        )


class OAuth2TokenRefreshError(OAuth2RedirectError):
    """
    Raised when an OAuth2 refresh token request fails with a 400/401/403 error.
    The stored token is no longer valid and the user must re-authenticate.

    Subclasses OAuth2RedirectError so that existing oauth2_exception checks
    match it automatically, triggering start_oauth2_dance() via check_for_oauth2.
    """

    def __init__(self, response_text: str) -> None:
        AxBIErrorException.__init__(
            self,
            AxBIError(
                message="OAuth2 token refresh failed, re-authentication required.",
                error_type=AxBIErrorType.OAUTH2_REDIRECT,
                level=ErrorLevel.WARNING,
                extra={"error": response_text},
            ),
        )


class OAuth2Error(AxBIErrorException):
    """
    Exception for when OAuth2 goes wrong.
    """

    def __init__(self, error: str):
        super().__init__(
            AxBIError(
                message="Something went wrong while doing OAuth2",
                error_type=AxBIErrorType.OAUTH2_REDIRECT_ERROR,
                level=ErrorLevel.ERROR,
                extra={"error": error},
            )
        )


class AxBIDisallowedSQLFunctionException(AxBIErrorException):
    """
    Disallowed function found on SQL statement
    """

    def __init__(self, functions: set[str]):
        super().__init__(
            AxBIError(
                message=f"SQL statement contains disallowed function(s): {functions}",
                error_type=AxBIErrorType.SYNTAX_ERROR,
                level=ErrorLevel.ERROR,
            )
        )


class AxBIDisallowedSQLTableException(AxBIErrorException):
    """
    Disallowed table/view found in SQL statement
    """

    def __init__(self, tables: set[str]):
        super().__init__(
            AxBIError(
                message=f"SQL statement references disallowed table(s): {tables}",
                error_type=AxBIErrorType.SYNTAX_ERROR,
                level=ErrorLevel.ERROR,
            )
        )


class AcquireDistributedLockFailedException(Exception):  # noqa: N818
    """
    Exception to signalize failure to acquire lock.
    """


class ReleaseDistributedLockFailedException(Exception):  # noqa: N818
    """
    Exception to signalize failure to release lock.
    """


class DatabaseNotFoundException(AxBIErrorException):
    status = 404

    def __init__(self, message: str):
        super().__init__(
            AxBIError(
                message=message,
                error_type=AxBIErrorType.DATABASE_NOT_FOUND_ERROR,
                level=ErrorLevel.ERROR,
            )
        )


class TableNotFoundException(AxBIErrorException):
    status = 404

    def __init__(self, message: str):
        super().__init__(
            AxBIError(
                message=message,
                error_type=AxBIErrorType.TABLE_NOT_FOUND_ERROR,
                level=ErrorLevel.ERROR,
            )
        )


class AxBIDMLNotAllowedException(AxBIErrorException):
    def __init__(self) -> None:
        error = AxBIError(
            message=_(
                "This database does not allow for DDL/DML, but the query mutates "
                "data. Please contact your administrator for more assistance."
            ),
            error_type=AxBIErrorType.DML_NOT_ALLOWED_ERROR,
            level=ErrorLevel.ERROR,
        )
        super().__init__(error)


class AxBIInvalidCTASException(AxBIErrorException):
    def __init__(self) -> None:
        error = AxBIError(
            message=_(
                "CTAS (create table as select) can only be run with a query where "
                "the last statement is a SELECT. Please make sure your query has "
                "a SELECT as its last statement. Then, try running your query again."
            ),
            error_type=AxBIErrorType.INVALID_CTAS_QUERY_ERROR,
            level=ErrorLevel.ERROR,
        )
        super().__init__(error)


class AxBIInvalidCVASException(AxBIErrorException):
    def __init__(self) -> None:
        error = AxBIError(
            message=_(
                "CVAS (create view as select) can only be run with a query with "
                "a single SELECT statement. Please make sure your query has only "
                "a SELECT statement. Then, try running your query again."
            ),
            error_type=AxBIErrorType.INVALID_CVAS_QUERY_ERROR,
            level=ErrorLevel.ERROR,
        )
        super().__init__(error)


class AxBIResultsBackendNotConfigureException(AxBIErrorException):
    def __init__(self) -> None:
        error = AxBIError(
            message=_("Results backend is not configured."),
            error_type=AxBIErrorType.RESULTS_BACKEND_NOT_CONFIGURED_ERROR,
            level=ErrorLevel.ERROR,
        )
        super().__init__(error)


class ScreenshotImageNotAvailableException(AxBIException):
    status = 404
