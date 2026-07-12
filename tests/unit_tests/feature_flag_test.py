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
from pytest_mock import MockerFixture

from axbi import is_feature_enabled
from axbi.config import (
    AX_SERVICES_BASE_URL,
    AX_SERVICES_INTERNAL_TOKEN,
    AX_SERVICES_TIMEOUT_SECONDS,
    DEFAULT_FEATURE_FLAGS,
)


def dummy_is_feature_enabled(feature_flag_name: str, default: bool = True) -> bool:
    return True if feature_flag_name.startswith("True_") else default


def test_existing_feature_flags(mocker: MockerFixture) -> None:
    """
    Test that ``is_feature_enabled`` reads flags correctly.
    """
    mocker.patch.dict(
        "axbi.extensions.feature_flag_manager._feature_flags",
        {"FOO": True},
        clear=True,
    )
    assert is_feature_enabled("FOO") is True


def test_nonexistent_feature_flags(mocker: MockerFixture) -> None:
    """
    Test that ``is_feature_enabled`` returns ``False`` when flag not set.
    """
    mocker.patch.dict(
        "axbi.extensions.feature_flag_manager._feature_flags", {}, clear=True
    )
    assert is_feature_enabled("FOO") is False


def test_is_feature_enabled(mocker: MockerFixture) -> None:
    """
    Test ``_is_feature_enabled_func``.
    """
    mocker.patch.dict(
        "axbi.extensions.feature_flag_manager._feature_flags",
        {"True_Flag1": False, "True_Flag2": True, "Flag3": False, "Flag4": True},
        clear=True,
    )
    mocker.patch(
        "axbi.extensions.feature_flag_manager._is_feature_enabled_func",
        dummy_is_feature_enabled,
    )

    assert is_feature_enabled("True_Flag1") is True
    assert is_feature_enabled("True_Flag2") is True
    assert is_feature_enabled("Flag3") is False
    assert is_feature_enabled("Flag4") is True


def test_runtime_modernization_feature_flags_default_disabled() -> None:
    """
    Test runtime modernization flags are opt-in.
    """

    assert DEFAULT_FEATURE_FLAGS["RUNTIME_MODERNIZATION"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_MCP_ORCHESTRATION"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_ASSET_SEARCH_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_ANNOTATION_LAYER_LIST_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_HEALTH_CHECK_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_DASHBOARD_LIST_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_CHART_LIST_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_DATASET_LIST_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_DATABASE_LIST_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_SAVED_QUERY_LIST_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_REPORT_LIST_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_TAG_LIST_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_TASK_LIST_SERVING"] is False
    assert DEFAULT_FEATURE_FLAGS["TS_METADATA_INDEX"] is False
    assert DEFAULT_FEATURE_FLAGS["RUST_SQL_KERNEL"] is False
    assert DEFAULT_FEATURE_FLAGS["RUST_ASSET_RANKING_KERNEL"] is False
    assert DEFAULT_FEATURE_FLAGS["RUST_CHART_VALIDATION_KERNEL"] is False
    assert DEFAULT_FEATURE_FLAGS["RUNTIME_SHADOW_EXECUTION"] is False


def test_ax_services_config_defaults() -> None:
    """
    Test AX services sidecar defaults are local and opt-in.
    """

    assert AX_SERVICES_BASE_URL == "http://127.0.0.1:5010"
    assert AX_SERVICES_TIMEOUT_SECONDS == 2.0
    assert AX_SERVICES_INTERNAL_TOKEN is None
