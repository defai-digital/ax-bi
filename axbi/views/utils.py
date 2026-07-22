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
from collections import defaultdict
from collections.abc import Callable
from functools import wraps
from typing import Any
from urllib import parse

import msgpack
import pyarrow as pa
from flask import current_app as app, has_request_context, redirect, request
from flask_appbuilder.security.sqla import models as ab_models
from flask_appbuilder.security.sqla.models import User
from flask_babel import _
from sqlalchemy.exc import NoResultFound

from axbi import appbuilder, dataframe, result_set
from axbi.axbi_typing import (
    ExplorableData,
    FlaskResponse,
)
from axbi.common.db_query_status import QueryStatus
from axbi.errors import AxBIError, AxBIErrorType, ErrorLevel
from axbi.exceptions import (
    AxBIException,
    AxBISecurityException,
    CacheLoadError,
    SerializationError,
)
from axbi.extensions import cache_manager, security_manager
from axbi.models.core import Database
from axbi.models.sql_lab import Query
from axbi.utils import json
from axbi.utils.decorators import stats_timing

logger = logging.getLogger(__name__)
stats_logger = app.config["STATS_LOGGER"]


def redirect_to_login(next_target: str | None = None) -> FlaskResponse:
    """Return a redirect response to the login view, preserving target URL.

    When ``next_target`` is ``None`` the current request path (including query
    string) is used, provided a request context is available. The resulting URL
    always remains relative, mirroring Flask-AppBuilder expectations.
    """

    login_url = appbuilder.get_url_for_login
    parsed = parse.urlparse(login_url)
    query = parse.parse_qs(parsed.query, keep_blank_values=True)

    target = next_target
    if target is None and has_request_context():
        if request.query_string:
            target = request.script_root + request.full_path.rstrip("?")
        else:
            target = request.script_root + request.path

    if target:
        query["next"] = [target]

    encoded_query = parse.urlencode(query, doseq=True)
    redirect_url = parse.urlunparse(parsed._replace(query=encoded_query))
    return redirect(redirect_url)


def sanitize_datasource_data(
    datasource_data: ExplorableData,
) -> dict[str, Any]:
    """
    Sanitize datasource data by removing sensitive database parameters.
    """
    if datasource_data:
        datasource_database = datasource_data.get("database")
        if datasource_database:
            datasource_database["parameters"] = {}

    return datasource_data  # type: ignore[return-value]


def bootstrap_user_data(user: User, include_perms: bool = False) -> dict[str, Any]:
    if user.is_anonymous:
        payload = {}
        user.roles = (security_manager.get_public_role(),)
    elif security_manager.is_guest_user(user):
        payload = {
            "username": user.username,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "isActive": user.is_active,
            "isAnonymous": user.is_anonymous,
        }
    else:
        payload = {
            "username": user.username,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "userId": user.id,
            "isActive": user.is_active,
            "isAnonymous": user.is_anonymous,
            "createdOn": user.created_on.isoformat() if user.created_on else None,
            "email": user.email,
            "loginCount": user.login_count,
        }

    if include_perms:
        roles, permissions = get_permissions(user)
        payload["roles"] = roles
        payload["permissions"] = permissions
        payload["groups"] = [group.name for group in getattr(user, "groups", [])]

    return payload


def get_config_value(key: str) -> Any:
    value = app.config[key]
    return value() if callable(value) else value


def get_permissions(
    user: User,
) -> tuple[dict[str, list[tuple[str]]], defaultdict[str, list[str]]]:
    if not user.roles and not user.groups:
        raise AttributeError("User object does not have roles or groups")

    data_permissions = defaultdict(set)
    roles_permissions = security_manager.get_user_roles_permissions(user)
    for _, permissions in roles_permissions.items():  # noqa: F402
        for permission in permissions:
            if permission[0] in ("datasource_access", "database_access"):
                data_permissions[permission[0]].add(permission[1])
    transformed_permissions = defaultdict(list)
    for perm in data_permissions:
        transformed_permissions[perm] = list(data_permissions[perm])
    return roles_permissions, transformed_permissions


# Re-exports from utils so views callers keep working; non-views layers should
# import from axbi.utils.viz_helpers / form_data (avoids Command/Task → views).
from axbi.utils.form_data import (  # noqa: E402, F401
    add_sqllab_custom_filters,
    build_extra_filters,
    CONTAINER_TYPES,
    get_dashboard_extra_filters,
    get_form_data,
    is_slice_in_container,
    JS_CONTROL_FORM_DATA_KEYS,
    loads_request_json,
    REJECTED_FORM_DATA_KEYS,
)
from axbi.utils.viz_helpers import get_datasource_info, get_viz  # noqa: E402, F401


def _deserialize_json_results_payload(payload: bytes | str) -> dict[str, Any]:
    with stats_timing("sqllab.query.results_backend_json_deserialize", stats_logger):
        try:
            ds_payload = json.loads(payload)
        except (TypeError, ValueError) as ex:
            raise SerializationError("Unable to deserialize payload") from ex

    if not isinstance(ds_payload, dict):
        raise SerializationError("Unexpected results payload")

    return ds_payload


def apply_display_max_row_limit(
    sql_results: dict[str, Any], rows: int | None = None
) -> dict[str, Any]:
    """
    Given a `sql_results` nested structure, applies a limit to the number of rows

    `sql_results` here is the nested structure coming out of sql_lab.get_sql_results, it
    contains metadata about the query, as well as the data set returned by the query.
    This method limits the number of rows adds a `displayLimitReached: True` flag to the
    metadata.

    :param sql_results: The results of a sql query from sql_lab.get_sql_results
    :param rows: The number of rows to apply a limit to
    :returns: The mutated sql_results structure
    """

    display_limit = rows or app.config["DISPLAY_MAX_ROW"]
    query = sql_results.get("query")
    result_rows = query.get("rows") if isinstance(query, dict) else None

    if (
        display_limit
        and sql_results.get("status") == QueryStatus.SUCCESS
        and isinstance(result_rows, int)
        and display_limit < result_rows
        and isinstance(sql_results.get("data"), list)
    ):
        sql_results["data"] = sql_results["data"][:display_limit]
        sql_results["displayLimitReached"] = True
    return sql_results


def check_resource_permissions(
    check_perms: Callable[..., Any],
) -> Callable[..., Any]:
    """
    A decorator for checking permissions on a request using the passed-in function.
    """

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            # check if the user can access the resource
            check_perms(*args, **kwargs)
            return f(*args, **kwargs)

        return wrapper

    return decorator


def check_explore_cache_perms(_self: Any, cache_key: str) -> None:
    """
    Loads async explore_json request data from cache and performs access check

    :param _self: the AxBI view instance
    :param cache_key: the cache key passed into /explore_json/data/
    :raises AxBISecurityException: If the user cannot access the resource
    """
    cached = cache_manager.cache.get(cache_key)
    if not cached:
        raise CacheLoadError("Cached data not found")

    check_datasource_perms(_self, form_data=cached["form_data"])


def check_datasource_perms(
    _self: Any,
    datasource_type: str | None = None,
    datasource_id: int | None = None,
    **kwargs: Any,
) -> None:
    """
    Check if user can access a cached response from explore_json.

    This function takes `self` since it must have the same signature as the
    the decorated method.

    :param datasource_type: The datasource type
    :param datasource_id: The datasource ID
    :raises AxBISecurityException: If the user cannot access the resource
    """

    form_data = kwargs["form_data"] if "form_data" in kwargs else get_form_data()[0]

    try:
        datasource_id, datasource_type = get_datasource_info(
            datasource_id, datasource_type, form_data
        )
    except AxBIException as ex:
        raise AxBISecurityException(
            AxBIError(
                error_type=AxBIErrorType.FAILED_FETCHING_DATASOURCE_INFO_ERROR,
                level=ErrorLevel.ERROR,
                message=str(ex),
            )
        ) from ex

    if datasource_type is None:
        raise AxBISecurityException(
            AxBIError(
                error_type=AxBIErrorType.UNKNOWN_DATASOURCE_TYPE_ERROR,
                level=ErrorLevel.ERROR,
                message=_("Could not determine datasource type"),
            )
        )

    try:
        viz_obj = get_viz(
            datasource_type=datasource_type,
            datasource_id=datasource_id,
            form_data=form_data,
            force=False,
        )
    except NoResultFound as ex:
        raise AxBISecurityException(
            AxBIError(
                error_type=AxBIErrorType.UNKNOWN_DATASOURCE_TYPE_ERROR,
                level=ErrorLevel.ERROR,
                message=_("Could not find viz object"),
            )
        ) from ex

    viz_obj.raise_for_access()


def _deserialize_results_payload(
    payload: bytes | str, query: Query, use_msgpack: bool | None = False
) -> dict[str, Any]:
    logger.debug("Deserializing from msgpack: %r", use_msgpack)
    if use_msgpack:
        with stats_timing(
            "sqllab.query.results_backend_msgpack_deserialize", stats_logger
        ):
            try:
                ds_payload = msgpack.loads(payload, raw=False)
            except (
                msgpack.exceptions.ExtraData,
                msgpack.exceptions.FormatError,
                msgpack.exceptions.StackError,
                TypeError,
                ValueError,
            ) as ex:
                raise SerializationError("Unable to deserialize payload") from ex

        if not isinstance(ds_payload, dict):
            raise SerializationError("Unexpected results payload")

        data = ds_payload.get("data")
        selected_columns = ds_payload.get("selected_columns")
        if not isinstance(data, bytes) or not isinstance(selected_columns, list):
            raise SerializationError("Unexpected results payload")
        if not all(isinstance(column, dict) for column in selected_columns):
            raise SerializationError("Unexpected results payload")

        with stats_timing("sqllab.query.results_backend_pa_deserialize", stats_logger):
            try:
                reader = pa.BufferReader(data)
                pa_table = pa.ipc.open_stream(reader).read_all()
            except (pa.ArrowException, TypeError, ValueError) as ex:
                raise SerializationError("Unable to deserialize table") from ex

        df = result_set.AxBIResultSet.convert_table_to_df(pa_table)
        ds_payload["data"] = dataframe.df_to_records(df) or []

        for column in selected_columns:
            if "name" in column:
                column["column_name"] = column.get("name")

        db_engine_spec = query.database.db_engine_spec
        all_columns, data, expanded_columns = db_engine_spec.expand_data(
            selected_columns, ds_payload["data"]
        )
        ds_payload.update(
            {"data": data, "columns": all_columns, "expanded_columns": expanded_columns}
        )

        return ds_payload

    return _deserialize_json_results_payload(payload)


def get_cta_schema_name(
    database: Database, user: ab_models.User, schema: str, sql: str
) -> str | None:
    func: Callable[[Database, ab_models.User, str, str], str] | None = app.config[
        "SQLLAB_CTAS_SCHEMA_NAME_FUNC"
    ]
    if not func:
        return None
    return func(database, user, schema, sql)
