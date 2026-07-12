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
"""Tests for subdirectory deployment features."""

from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

from werkzeug.test import EnvironBuilder

from axbi.app import AppRootMiddleware
from axbi.views.utils import redirect_to_login
from tests.integration_tests.base_tests import AxBITestCase


class TestSubdirectoryDeployments(AxBITestCase):
    """Test subdirectory deployment features including middleware."""

    def setUp(self):
        super().setUp()

    def test_former_brand_route_is_not_registered(self):
        """Only AX BI route prefixes are exposed by the application."""
        former_brand_route = "/" + "super" + "set/welcome/"
        response = self.client.get(former_brand_route)

        assert response.status_code == 404

    # AppRootMiddleware tests (core subdirectory deployment functionality)

    def test_app_root_middleware_path_handling(self):
        """Test middleware correctly handles path prefixes."""
        # Create a mock WSGI app
        mock_app = MagicMock()
        mock_app.return_value = [b"response"]

        middleware = AppRootMiddleware(mock_app, "/ax-bi")

        # Test with correct prefix
        environ = EnvironBuilder("/ax-bi/dashboard").get_environ()
        start_response = MagicMock()

        result = list(middleware(environ, start_response))

        # Should call the wrapped app
        mock_app.assert_called_once()
        called_environ = mock_app.call_args[0][0]

        # PATH_INFO should be stripped of prefix
        assert called_environ["PATH_INFO"] == "/dashboard"
        # SCRIPT_NAME should be set to the prefix
        assert called_environ["SCRIPT_NAME"] == "/ax-bi"
        assert result == [b"response"]

    def test_app_root_middleware_wrong_path_returns_404(self):
        """Test middleware returns 404 for incorrect paths."""
        # Create a mock WSGI app
        mock_app = MagicMock()

        middleware = AppRootMiddleware(mock_app, "/ax-bi")

        # Test with incorrect prefix
        environ = EnvironBuilder("/wrong/path").get_environ()
        start_response = MagicMock()

        list(middleware(environ, start_response))

        # Should not call the wrapped app
        mock_app.assert_not_called()

        # Should return 404 response
        start_response.assert_called_once()
        status = start_response.call_args[0][0]
        assert "404" in status

    def test_app_root_middleware_root_path_handling(self):
        """Test middleware handles root path correctly."""
        # Create a mock WSGI app
        mock_app = MagicMock()
        mock_app.return_value = [b"response"]

        middleware = AppRootMiddleware(mock_app, "/ax-bi")

        # Test with exact prefix path
        environ = EnvironBuilder("/ax-bi").get_environ()
        start_response = MagicMock()

        list(middleware(environ, start_response))

        # Should call the wrapped app
        mock_app.assert_called_once()
        called_environ = mock_app.call_args[0][0]

        # PATH_INFO should be empty
        assert called_environ["PATH_INFO"] == ""
        # SCRIPT_NAME should be set to the prefix
        assert called_environ["SCRIPT_NAME"] == "/ax-bi"

    def test_redirect_to_login_with_app_root(self):
        """Test that redirect_to_login includes app root in next parameter."""
        with self.app.test_request_context(
            "/ax-bi/welcome/",
            environ_overrides={"SCRIPT_NAME": "/analytics"},
        ):
            response = redirect_to_login()
            parsed_url = urlparse(response.location)
            query_params = parse_qs(parsed_url.query)

            # The next parameter should include the app root prefix
            assert "next" in query_params
            assert query_params["next"][0] == "/analytics/ax-bi/welcome/"

    def test_redirect_to_login_with_query_string_and_app_root(self):
        """Test that redirect_to_login preserves query string with app root."""
        with self.app.test_request_context(
            "/ax-bi/welcome/?foo=bar",
            environ_overrides={"SCRIPT_NAME": "/analytics"},
        ):
            response = redirect_to_login()
            parsed_url = urlparse(response.location)
            query_params = parse_qs(parsed_url.query)

            # The next parameter should include both app root and query string
            assert "next" in query_params
            assert query_params["next"][0] == "/analytics/ax-bi/welcome/?foo=bar"

    def test_redirect_to_login_without_app_root(self):
        """Test that redirect_to_login works without app root (no regression)."""
        with self.app.test_request_context("/ax-bi/welcome/"):
            response = redirect_to_login()
            parsed_url = urlparse(response.location)
            query_params = parse_qs(parsed_url.query)

            # The next parameter should be the path without any prefix
            assert "next" in query_params
            assert query_params["next"][0] == "/ax-bi/welcome/"

    def test_redirect_to_login_with_custom_target_and_app_root(self):
        """Test that redirect_to_login respects custom target parameter."""
        with self.app.test_request_context(
            "/some/other/path",
            environ_overrides={"SCRIPT_NAME": "/analytics"},
        ):
            # When next_target is explicitly provided, it should be used as-is
            custom_target = "/custom/target"
            response = redirect_to_login(next_target=custom_target)
            parsed_url = urlparse(response.location)
            query_params = parse_qs(parsed_url.query)

            assert "next" in query_params
            assert query_params["next"][0] == custom_target
