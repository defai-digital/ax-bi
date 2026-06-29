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
"""Tests for ``superset/views/upload.py``."""

from unittest.mock import MagicMock, patch

import pytest
from werkzeug.exceptions import NotFound


def test_upload_data_view_uses_database_upload_permission() -> None:
    """
    The zero-config upload page must be reachable to roles granted
    ``can_upload`` on Database, matching the upload REST APIs.
    """
    from superset.views.upload import UploadDataView

    assert UploadDataView.class_permission_name == "Database"
    assert UploadDataView.index._permission_name == "upload"  # pylint: disable=protected-access


def test_upload_data_view_returns_404_when_feature_disabled(
    app_context: None,
) -> None:
    """
    The upload page should fail closed when local upload is disabled.
    """
    from superset.views.upload import UploadDataView

    view = UploadDataView()
    view.appbuilder = MagicMock()
    view.appbuilder.sm.has_access.return_value = True

    with patch("superset.views.upload.is_feature_enabled", return_value=False):
        with pytest.raises(NotFound):
            view.index()
