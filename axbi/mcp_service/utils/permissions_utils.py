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

"""Narrow permission adapters used by the MCP service."""

from __future__ import annotations

from typing import Any

from flask import g, has_app_context
from flask_appbuilder.security.sqla.models import User


def get_current_user() -> User | None:
    """Return the authenticated Flask user when an app context is active."""
    if not has_app_context():
        return None
    return getattr(g, "user", None)


def current_user_can_access(permission: str, view_name: str) -> bool:
    """Return whether the current user has access to a view permission."""
    from axbi import security_manager

    return security_manager.can_access(permission, view_name)


def current_user_can_access_database(database: Any) -> bool:
    """Return whether the current user has access to a database."""
    from axbi import security_manager

    return security_manager.can_access_database(database)


def user_can_access_dataset_permission(permission: str) -> bool:
    """Return whether the current user has a Dataset-level permission."""
    return current_user_can_access(permission, "Dataset")
