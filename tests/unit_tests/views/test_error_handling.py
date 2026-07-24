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

from flask import Flask
from flask_babel import Babel
from sqlalchemy.exc import IntegrityError

from axbi.exceptions import AxBIException
from axbi.views.error_handling import handle_api_exception, set_app_error_handlers


def test_global_exception_handler_redacts_internal_details() -> None:
    """Unhandled exception text must remain in server logs, not client payloads."""
    app = Flask(__name__)
    Babel(app)
    app.config["DEBUG"] = True
    set_app_error_handlers(app)

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("password=secret-value")

    response = app.test_client().get(
        "/failure",
        headers={"accept": "application/json"},
    )

    assert response.status_code == 500
    assert response.get_json()["errors"][0]["message"] == (
        "An unexpected error occurred"
    )
    assert b"secret-value" not in response.data


def test_api_database_exception_redacts_statement_and_parameters() -> None:
    """SQLAlchemy exceptions must not expose SQL or bound values to API clients."""
    app = Flask(__name__)

    @handle_api_exception
    def failing_view(_: object) -> None:
        raise IntegrityError(
            "INSERT INTO users(password) VALUES (:password)",
            {"password": "secret-value"},
            RuntimeError("constraint failed"),
        )

    with app.test_request_context("/failure"):
        response = app.make_response(failing_view(object()))

    assert response.status_code == 422
    assert response.get_json()["error"] == "A database error occurred"
    assert b"secret-value" not in response.data


def test_api_axbi_exception_redacts_internal_details() -> None:
    """Legacy application exceptions must not expose their message to clients."""
    app = Flask(__name__)

    @handle_api_exception
    def failing_view(_: object) -> None:
        raise AxBIException("password=secret-value")

    with app.test_request_context("/failure"):
        response = app.make_response(failing_view(object()))

    assert response.status_code == 500
    assert response.get_json()["error"] == "An unexpected error occurred"
    assert b"secret-value" not in response.data
