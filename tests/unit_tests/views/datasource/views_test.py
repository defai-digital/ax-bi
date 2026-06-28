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
"""Unit tests for resource-level authorization in superset/views/datasource/views.py.

Tests use ``inspect.unwrap`` to call the underlying view logic directly,
bypassing the Flask-AppBuilder permission decorator machinery.
"""

import inspect
from unittest.mock import MagicMock, patch

import pytest

from superset.errors import ErrorLevel, SupersetError, SupersetErrorType
from superset.exceptions import SupersetSecurityException
from superset.utils import json as superset_json


def _security_exception() -> SupersetSecurityException:
    return SupersetSecurityException(
        SupersetError(
            message="Access denied",
            error_type=SupersetErrorType.DATASOURCE_SECURITY_ACCESS_ERROR,
            level=ErrorLevel.WARNING,
        )
    )


def _get_view_func(name: str):
    """Return the unwrapped body of a Datasource view method."""
    from superset.views.datasource.views import Datasource

    return inspect.unwrap(getattr(Datasource, name))


def _view_self() -> MagicMock:
    """Create a minimal stand-in for a Datasource view instance."""
    self = MagicMock()
    self.json_response = MagicMock(return_value="ok")
    return self


# ---------------------------------------------------------------------------
# Datasource.get
# ---------------------------------------------------------------------------


@patch("superset.views.datasource.views.security_manager", new_callable=MagicMock)
@patch("superset.views.datasource.views.DatasourceDAO.get_datasource")
def test_get_raises_when_access_denied(
    mock_get_datasource: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    """raise_for_access is called and propagates for unauthorised callers."""
    mock_datasource = MagicMock()
    mock_get_datasource.return_value = mock_datasource
    mock_security_manager.raise_for_access.side_effect = _security_exception()

    raw_get = _get_view_func("get")
    with pytest.raises(SupersetSecurityException):
        raw_get(_view_self(), "table", 1)

    mock_security_manager.raise_for_access.assert_called_once_with(
        datasource=mock_datasource
    )


@patch("superset.views.datasource.views.sanitize_datasource_data")
@patch("superset.views.datasource.views.security_manager", new_callable=MagicMock)
@patch("superset.views.datasource.views.DatasourceDAO.get_datasource")
def test_get_succeeds_for_authorised_user(
    mock_get_datasource: MagicMock,
    mock_security_manager: MagicMock,
    mock_sanitize: MagicMock,
) -> None:
    """raise_for_access is called without raising; sanitized data is returned."""
    mock_datasource = MagicMock()
    mock_datasource.data = {"id": 1}
    mock_get_datasource.return_value = mock_datasource
    mock_security_manager.raise_for_access.return_value = None
    mock_sanitize.return_value = {"id": 1}

    view = _view_self()
    raw_get = _get_view_func("get")
    raw_get(view, "table", 1)

    mock_security_manager.raise_for_access.assert_called_once_with(
        datasource=mock_datasource
    )
    view.json_response.assert_called_once_with({"id": 1})


# ---------------------------------------------------------------------------
# Datasource.external_metadata
# ---------------------------------------------------------------------------


@patch("superset.views.datasource.views.security_manager", new_callable=MagicMock)
@patch("superset.views.datasource.views.DatasourceDAO.get_datasource")
def test_external_metadata_raises_when_access_denied(
    mock_get_datasource: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    mock_datasource = MagicMock()
    mock_get_datasource.return_value = mock_datasource
    mock_security_manager.raise_for_access.side_effect = _security_exception()

    raw_fn = _get_view_func("external_metadata")
    with pytest.raises(SupersetSecurityException):
        raw_fn(_view_self(), "table", 1)

    mock_security_manager.raise_for_access.assert_called_once_with(
        datasource=mock_datasource
    )


@patch("superset.views.datasource.views.security_manager", new_callable=MagicMock)
@patch("superset.views.datasource.views.DatasourceDAO.get_datasource")
def test_external_metadata_succeeds_for_authorised_user(
    mock_get_datasource: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    mock_datasource = MagicMock()
    mock_datasource.external_metadata.return_value = [{"name": "col1"}]
    mock_get_datasource.return_value = mock_datasource
    mock_security_manager.raise_for_access.return_value = None

    view = _view_self()
    raw_fn = _get_view_func("external_metadata")
    raw_fn(view, "table", 1)

    mock_security_manager.raise_for_access.assert_called_once_with(
        datasource=mock_datasource
    )
    view.json_response.assert_called_once_with([{"name": "col1"}])


# ---------------------------------------------------------------------------
# Datasource.external_metadata_by_name
# ---------------------------------------------------------------------------


@patch("superset.views.datasource.views.security_manager", new_callable=MagicMock)
@patch("superset.views.datasource.views.SqlaTable.get_datasource_by_name")
@patch("superset.views.datasource.views.ExternalMetadataSchema")
def test_external_metadata_by_name_known_datasource_raises_when_access_denied(
    mock_schema_cls: MagicMock,
    mock_get_by_name: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    """When a datasource exists, raise_for_access(datasource=...) is enforced."""
    params = {
        "database_name": "mydb",
        "schema_name": "public",
        "table_name": "private_table",
    }
    mock_schema_cls.return_value.load.return_value = params

    mock_datasource = MagicMock()
    mock_get_by_name.return_value = mock_datasource
    mock_security_manager.raise_for_access.side_effect = _security_exception()

    raw_fn = _get_view_func("external_metadata_by_name")
    with pytest.raises(SupersetSecurityException):
        raw_fn(_view_self(), rison=params)

    mock_security_manager.raise_for_access.assert_called_once_with(
        datasource=mock_datasource
    )


@patch("superset.views.datasource.views.security_manager", new_callable=MagicMock)
@patch("superset.views.datasource.views.SqlaTable.get_datasource_by_name")
@patch("superset.views.datasource.views.ExternalMetadataSchema")
@patch("superset.views.datasource.views.db")
def test_external_metadata_by_name_no_datasource_raises_when_access_denied(
    mock_db: MagicMock,
    mock_schema_cls: MagicMock,
    mock_get_by_name: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    """When no datasource exists, raise_for_access(database=..., table=...) runs."""
    params = {
        "database_name": "mydb",
        "schema_name": "public",
        "table_name": "new_table",
    }
    mock_schema_cls.return_value.load.return_value = params
    mock_get_by_name.return_value = None

    mock_database = MagicMock()
    mock_db.session.query.return_value.filter_by.return_value.one.return_value = (
        mock_database
    )
    mock_security_manager.raise_for_access.side_effect = _security_exception()

    raw_fn = _get_view_func("external_metadata_by_name")
    with pytest.raises(SupersetSecurityException):
        raw_fn(_view_self(), rison=params)

    mock_security_manager.raise_for_access.assert_called_once()
    call_kwargs = mock_security_manager.raise_for_access.call_args.kwargs
    assert call_kwargs["database"] is mock_database
    assert call_kwargs["table"].table == "new_table"
    assert call_kwargs["table"].schema == "public"


def test_samples_rejects_malformed_json_body() -> None:
    """Malformed samples payloads should return schema validation errors."""
    from flask import Flask

    raw_samples = _get_view_func("samples")
    app = Flask(__name__)
    with app.test_request_context(
        "/datasource/samples?datasource_id=1&datasource_type=table",
        method="POST",
        data="{malformed",
        content_type="application/json",
    ):
        response = raw_samples(_view_self())

    assert response.status_code == 400
    assert response.get_json() == {"message": {"_schema": ["Invalid input type."]}}


# ---------------------------------------------------------------------------
# Datasource.save — ownership bypass prevention
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        "{bad json",
        "[]",
        '"bad"',
        "1",
        "null",
        "{}",
        '{"id": 1, "type": "table", "database": []}',
        '{"id": 1, "type": "table", "database": {"id": 1}}',
        '{"id": 1, "type": "table", "database": {"id": 1}, "columns": {}}',
        '{"id": 1, "type": "table", "database": {"id": 1}, "columns": [{}]}',
        '{"id": 1, "type": "table", "database": {"id": 1}, "columns": ["bad"]}',
        (
            '{"id": 1, "type": "table", "database": {"id": 1}, '
            '"columns": [{"column_name": 1}]}'
        ),
    ],
)
@patch(
    "superset.views.datasource.views._", side_effect=lambda message, **kwargs: message
)
@patch("superset.views.datasource.views.json_error_response", return_value="error")
@patch("superset.views.datasource.views.DatasourceDAO.get_datasource")
def test_save_rejects_malformed_datasource_payload(
    mock_get_datasource: MagicMock,
    mock_json_error_response: MagicMock,
    mock_gettext: MagicMock,
    payload: str,
) -> None:
    """Malformed datasource payloads should fail before datasource lookup."""
    from flask import Flask

    raw_save = _get_view_func("save")
    app = Flask(__name__)
    with app.test_request_context(
        "/datasource/save/",
        method="POST",
        data={"data": payload},
    ):
        assert raw_save(_view_self()) == "error"

    mock_get_datasource.assert_not_called()
    mock_json_error_response.assert_called_once_with(
        "Invalid datasource payload.", status=400
    )
    mock_gettext.assert_called_once_with("Invalid datasource payload.")


@patch("superset.views.datasource.views.security_manager", new_callable=MagicMock)
@patch("superset.views.datasource.views.DatasourceDAO.get_datasource")
def test_save_always_checks_ownership_even_without_owners_field(
    mock_get_datasource: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    """Ownership check runs even when 'owners' is absent from the payload."""
    mock_orm = MagicMock()
    mock_orm.owner_class = MagicMock()  # not None — model supports ownership
    mock_get_datasource.return_value = mock_orm
    mock_security_manager.raise_for_ownership.side_effect = SupersetSecurityException(
        SupersetError(
            message="Not an owner",
            error_type=SupersetErrorType.DATASOURCE_SECURITY_ACCESS_ERROR,
            level=ErrorLevel.WARNING,
        )
    )

    from flask import Flask

    from superset.commands.dataset.exceptions import DatasetForbiddenError

    raw_save = _get_view_func("save")
    app = Flask(__name__)
    with app.test_request_context(
        "/datasource/save/",
        method="POST",
        data={
            "data": superset_json.dumps(
                {
                    "id": 1,
                    "type": "table",
                    "database": {"id": 1},
                    "columns": [],
                    # 'owners' intentionally omitted
                }
            )
        },
    ):
        with pytest.raises(DatasetForbiddenError):
            raw_save(_view_self())

    mock_security_manager.raise_for_ownership.assert_called_once_with(mock_orm)


@patch("superset.views.datasource.views.sanitize_datasource_data", return_value={})
@patch("superset.views.datasource.views.populate_owner_list", return_value=[])
@patch("superset.views.datasource.views.DatasourceDAO.get_datasource")
@patch("superset.views.datasource.views.db")
def test_save_accepts_missing_owners_after_ownership_check(
    mock_db: MagicMock,
    mock_get_datasource: MagicMock,
    mock_populate_owner_list: MagicMock,
    mock_sanitize_datasource_data: MagicMock,
) -> None:
    """Omitted owners should use the owner helper's default handling."""
    mock_orm = MagicMock()
    mock_orm.owner_class = None
    mock_orm.data = {"id": 1}
    mock_get_datasource.return_value = mock_orm

    from flask import Flask

    raw_save = _get_view_func("save")
    app = Flask(__name__)
    with app.test_request_context(
        "/datasource/save/",
        method="POST",
        data={
            "data": superset_json.dumps(
                {
                    "id": 1,
                    "type": "table",
                    "database": {"id": 1},
                    "columns": [],
                }
            )
        },
    ):
        assert raw_save(_view_self()) == "ok"

    mock_populate_owner_list.assert_called_once_with(None, default_to_user=False)
    mock_orm.update_from_object.assert_called_once()
    mock_db.session.commit.assert_called_once()


@patch("superset.views.datasource.views.security_manager", new_callable=MagicMock)
@patch("superset.views.datasource.views.DatasourceDAO.get_datasource")
def test_save_non_owner_with_owners_field_is_rejected(
    mock_get_datasource: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    """A non-owner cannot use the save endpoint even when supplying an owners list."""
    mock_orm = MagicMock()
    mock_orm.owner_class = MagicMock()
    mock_get_datasource.return_value = mock_orm
    mock_security_manager.raise_for_ownership.side_effect = SupersetSecurityException(
        SupersetError(
            message="Not an owner",
            error_type=SupersetErrorType.DATASOURCE_SECURITY_ACCESS_ERROR,
            level=ErrorLevel.WARNING,
        )
    )

    from flask import Flask

    from superset.commands.dataset.exceptions import DatasetForbiddenError

    raw_save = _get_view_func("save")
    app = Flask(__name__)
    with app.test_request_context(
        "/datasource/save/",
        method="POST",
        data={
            "data": superset_json.dumps(
                {
                    "id": 1,
                    "type": "table",
                    "database": {"id": 1},
                    "columns": [],
                    "owners": [99],  # attacker-supplied owners list
                }
            )
        },
    ):
        with pytest.raises(DatasetForbiddenError):
            raw_save(_view_self())

    mock_security_manager.raise_for_ownership.assert_called_once_with(mock_orm)
