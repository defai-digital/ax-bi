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
import logging
import re
from typing import Any

from flask import current_app as app
from flask_babel import gettext as __

from axbi.commands.base import BaseCommand
from axbi.commands.database.exceptions import (
    DatabaseNotFoundError,
    NoValidatorConfigFoundError,
    NoValidatorFoundError,
    ValidatorSQL400Error,
    ValidatorSQLError,
    ValidatorSQLUnexpectedError,
)
from axbi.daos.database import DatabaseDAO
from axbi.errors import AxBIError, AxBIErrorType, ErrorLevel
from axbi.exceptions import (
    AxBISyntaxErrorException,
    AxBITemplateException,
)
from axbi.jinja_context import get_template_processor
from axbi.models.core import Database
from axbi.sql_validators import get_validator_by_name
from axbi.sql_validators.base import BaseSQLValidator
from axbi.utils import core as utils

logger = logging.getLogger(__name__)


class ValidateSQLCommand(BaseCommand):
    def __init__(self, model_id: int, data: dict[str, Any]):
        self._properties = data.copy()
        self._model_id = model_id
        self._model: Database | None = None
        self._validator: type[BaseSQLValidator] | None = None

    def run(self) -> list[dict[str, Any]]:
        """
        Validates a SQL statement

        :return: A List of SQLValidationAnnotation
        :raises: DatabaseNotFoundError, NoValidatorConfigFoundError
          NoValidatorFoundError, ValidatorSQLUnexpectedError, ValidatorSQLError
          ValidatorSQL400Error
        """
        self.validate()
        if not self._validator or not self._model:
            raise ValidatorSQLUnexpectedError()
        sql = self._properties["sql"]
        catalog = self._properties.get("catalog")
        schema = self._properties.get("schema")
        template_params = self._properties.get("template_params") or {}

        try:
            # Render Jinja templates to handle template syntax before
            # validation. Note: The ENABLE_TEMPLATE_PROCESSING feature flag is
            # checked within get_template_processor(), which returns
            # NoOpTemplateProcessor when disabled. Template processing errors
            # (e.g., undefined filters, syntax errors) are caught by this
            # exception handler and surfaced to the client as
            # ValidatorSQLError or ValidatorSQL400Error with appropriate error
            # messages.
            template_processor = get_template_processor(self._model)
            # process_template() renders Jinja2 templates and always returns a
            # new string (does not mutate the input SQL). May raise
            # AxBISyntaxErrorException for template syntax errors or
            # AxBITemplateException for internal errors.
            sql = template_processor.process_template(sql, **template_params)

            timeout = app.config["SQLLAB_VALIDATION_TIMEOUT"]
            timeout_msg = f"The query exceeded the {timeout} seconds timeout."
            with utils.timeout(seconds=timeout, error_message=timeout_msg):
                errors = self._validator.validate(sql, catalog, schema, self._model)
            return [err.to_dict() for err in errors]
        except AxBISyntaxErrorException as ex:
            # Template syntax errors (e.g., invalid Jinja2 syntax, undefined variables)
            # These contain detailed error information including line numbers
            logger.warning(
                "Template syntax error during SQL validation",
                extra={"errors": [err.message for err in ex.errors]},
            )
            error = (
                ex.errors[0]
                if ex.errors
                else AxBIError(
                    message=__("Template processing failed with a syntax error"),
                    error_type=AxBIErrorType.GENERIC_COMMAND_ERROR,
                    level=ErrorLevel.ERROR,
                )
            )
            raise ValidatorSQL400Error(error) from ex
        except AxBITemplateException as ex:
            # Internal template processing errors (e.g., recursion, unexpected failures)
            logger.error(
                "Template processing error during SQL validation", exc_info=True
            )
            axbi_error = AxBIError(
                message=__(
                    "Template processing failed: %(ex)s",
                    ex=str(ex),
                ),
                error_type=AxBIErrorType.GENERIC_COMMAND_ERROR,
                level=ErrorLevel.ERROR,
            )
            raise ValidatorSQL400Error(axbi_error) from ex
        except Exception as ex:
            logger.exception(ex)
            axbi_error = AxBIError(
                message=__(
                    "%(validator)s was unable to check your query.\n"
                    "Please recheck your query.\n"
                    "Exception: %(ex)s",
                    validator=self._validator.name,
                    ex=ex,
                ),
                error_type=AxBIErrorType.GENERIC_DB_ENGINE_ERROR,
                level=ErrorLevel.ERROR,
            )

            # Return as a 400 if the database error message says we got a 4xx error
            if re.search(r"([\W]|^)4\d{2}([\W]|$)", str(ex)):
                raise ValidatorSQL400Error(axbi_error) from ex
            raise ValidatorSQLError(axbi_error) from ex

    def validate(self) -> None:
        # Validate/populate model exists
        self._model = DatabaseDAO.find_by_id(self._model_id)
        if not self._model:
            raise DatabaseNotFoundError()

        spec = self._model.db_engine_spec
        validators_by_engine = app.config["SQL_VALIDATORS_BY_ENGINE"]
        if not validators_by_engine or spec.engine not in validators_by_engine:
            raise NoValidatorConfigFoundError(
                AxBIError(
                    message=__(
                        "no SQL validator is configured for %(engine_spec)s",
                        engine_spec=spec.engine,
                    ),
                    error_type=AxBIErrorType.GENERIC_DB_ENGINE_ERROR,
                    level=ErrorLevel.ERROR,
                ),
            )
        validator_name = validators_by_engine[spec.engine]
        self._validator = get_validator_by_name(validator_name)
        if not self._validator:
            raise NoValidatorFoundError(
                AxBIError(
                    message=__(
                        "No validator named %(validator_name)s found "
                        "(configured for the %(engine_spec)s engine)",
                        validator_name=validator_name,
                        engine_spec=spec.engine,
                    ),
                    error_type=AxBIErrorType.GENERIC_DB_ENGINE_ERROR,
                    level=ErrorLevel.ERROR,
                ),
            )
