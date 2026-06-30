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

import uuid
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from parameterized import parameterized

from superset.models.slice import id_or_uuid_filter, Slice


class TestSlice:
    """Test cases for Slice model functionality."""

    @parameterized.expand(
        [
            ("numeric_id", "123"),
            ("uuid_string", "550e8400-e29b-41d4-a716-446655440000"),
        ]
    )
    def test_slice_get_calls_filter_correctly(self, test_name, id_or_uuid):
        """Test Slice.get() calls filter() correctly for ID and UUID."""
        with patch("superset.models.slice.db") as mock_db:
            # Setup mock chain
            mock_query = MagicMock()
            mock_filtered_query = MagicMock()
            mock_db.session.query.return_value = mock_query
            mock_query.filter.return_value = mock_filtered_query
            mock_filtered_query.one_or_none.return_value = None

            # Call the method
            result = Slice.get(id_or_uuid)

            # Verify correct methods called
            mock_db.session.query.assert_called_once_with(Slice)
            mock_query.filter.assert_called_once()  # Not filter_by!
            mock_filtered_query.one_or_none.assert_called_once()
            assert result is None

    @parameterized.expand(
        [
            ("numeric_id", "123"),
            ("large_id", "999999"),
            ("uuid_string", str(uuid.uuid4())),
        ]
    )
    def test_slice_get_no_type_error(self, test_name, input_value):
        """Verify Slice.get() doesn't raise TypeError for various inputs."""
        try:
            result = Slice.get(input_value)
            # Success - no TypeError, result can be None or a Slice
            assert result is None or hasattr(result, "id")
        except TypeError as e:
            if "filter_by() takes 1 positional argument" in str(e):
                pytest.fail(
                    f"filter_by() bug exists: Slice.get('{input_value}') failed with {e}"  # noqa: E501
                )
            else:
                raise

    @parameterized.expand(
        [
            ("numeric_id", "123"),
            ("uuid_format", "550e8400-e29b-41d4-a716-446655440000"),
            ("invalid_string", "not-a-number"),
            ("integer_id", 123),
        ]
    )
    def test_id_or_uuid_filter(self, test_name, input_value):
        """Test id_or_uuid_filter returns correct BinaryExpression."""
        result = id_or_uuid_filter(input_value)
        assert result is not None

    def test_datasource_url_returns_none_when_datasource_lacks_explore_url(self):
        """datasource_url() must not raise when the datasource has no explore_url.

        Charts whose datasource resolves to a Query (or any other type without
        explore_url) used to raise AttributeError, which caused the entire chart
        list API response to fail instead of just skipping that one chart.
        """
        slc = Slice()
        slc.id = 1

        # Simulate a datasource object that does NOT have explore_url (e.g. Query)
        mock_datasource = MagicMock(spec=[])  # spec=[] means no attributes at all
        slc.table = mock_datasource

        result = slc.datasource_url()
        assert result is None

    def test_datasource_url_returns_explore_url_when_present(self):
        """datasource_url() returns the datasource explore_url when it exists."""
        slc = Slice()
        slc.id = 1

        mock_table = MagicMock()
        mock_table.explore_url = "/explore/?datasource_type=table&datasource_id=1"
        slc.table = mock_table

        result = slc.datasource_url()
        assert result == "/explore/?datasource_type=table&datasource_id=1"

    def test_datasource_url_returns_none_when_no_datasource(self):
        """datasource_url() returns None when there is no datasource."""
        slc = Slice()
        slc.id = 1
        slc.table = None

        result = slc.datasource_url()
        assert result is None

    def test_form_data_ignores_non_object_params(self):
        """form_data should tolerate valid JSON that is not an object."""
        slc = Slice(
            id=1,
            datasource_id=2,
            datasource_type="table",
            viz_type="table",
            params="[]",
        )

        assert slc.form_data == {
            "slice_id": 1,
            "viz_type": "table",
            "datasource": "2__table",
        }

    def test_form_data_ignores_malformed_params(self):
        """form_data should tolerate malformed chart params."""
        slc = Slice(
            id=1,
            datasource_id=2,
            datasource_type="table",
            viz_type="table",
            params="{malformed",
        )

        assert slc.form_data == {
            "slice_id": 1,
            "viz_type": "table",
            "datasource": "2__table",
        }

    def test_form_data_includes_zero_cache_timeout(self):
        """form_data should preserve an explicit zero cache timeout."""
        slc = Slice(
            id=1,
            datasource_id=2,
            datasource_type="table",
            viz_type="table",
            cache_timeout=0,
            params="{}",
        )

        assert slc.form_data["cache_timeout"] == 0

    def test_get_query_context_ignores_non_object_json(self):
        """Non-object query_context JSON should not reach the factory."""
        slc = Slice(query_context="[]")
        slc.query_context_factory = MagicMock()

        assert slc.get_query_context() is None
        slc.query_context_factory.create.assert_not_called()

    def test_data_handles_missing_changed_on(self, app: Any):
        """Chart data serialization should tolerate incomplete rows."""
        slc = Slice(
            id=1,
            datasource_id=2,
            datasource_type="table",
            viz_type="table",
            params="{}",
            changed_on=None,
        )

        data = slc.data

        assert data["changed_on"] is None
        assert data["changed_on_humanized"] is None

    def test_icons_escapes_datasource_html(self):
        """icons must HTML-escape the datasource name and edit URL."""
        slc = Slice()
        with (
            patch.object(
                Slice,
                "datasource_edit_url",
                new_callable=PropertyMock,
                return_value='/x"onmouseover=alert(1)',
            ),
            patch.object(
                Slice,
                "datasource",
                new_callable=PropertyMock,
                return_value="<img src=x onerror=alert(1)>",
            ),
        ):
            html = slc.icons

        # The injected tag and attribute-breakout quote are escaped.
        assert "<img" not in html
        assert '"onmouseover' not in html
