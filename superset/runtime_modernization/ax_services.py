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
"""Python client for the AX-BI TypeScript sidecar."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import requests

DEFAULT_AX_SERVICES_BASE_URL = "http://127.0.0.1:5010"
DEFAULT_AX_SERVICES_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class AxServicesConfig:
    """Configuration for calls from Superset to ax-services."""

    base_url: str = DEFAULT_AX_SERVICES_BASE_URL
    timeout_seconds: float = DEFAULT_AX_SERVICES_TIMEOUT_SECONDS
    internal_token: str | None = None

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "AxServicesConfig":
        """Build sidecar config from a Flask app config mapping."""

        return cls(
            base_url=str(
                config.get("AX_SERVICES_BASE_URL", DEFAULT_AX_SERVICES_BASE_URL)
            ).rstrip("/"),
            timeout_seconds=float(
                config.get(
                    "AX_SERVICES_TIMEOUT_SECONDS",
                    DEFAULT_AX_SERVICES_TIMEOUT_SECONDS,
                )
            ),
            internal_token=config.get("AX_SERVICES_INTERNAL_TOKEN"),
        )


@dataclass(frozen=True, slots=True)
class AxServicesResponse:
    """Response envelope for ax-services calls."""

    ok: bool
    status_code: int | None
    payload: dict[str, Any] | None = None
    error: str | None = None


class AxServicesClient:
    """Small HTTP client for runtime-modernization sidecar calls."""

    def __init__(
        self,
        config: AxServicesConfig,
        session: requests.Session | None = None,
    ) -> None:
        self._config = config
        self._session = session or requests.Session()

    def health(self, request_id: str | None = None) -> AxServicesResponse:
        """Call the sidecar health endpoint."""

        return self.get_json("/health", request_id=request_id)

    def ready(self, request_id: str | None = None) -> AxServicesResponse:
        """Call the sidecar readiness endpoint."""

        return self.get_json("/ready", request_id=request_id)

    def metadata(self, request_id: str | None = None) -> AxServicesResponse:
        """Call the sidecar Superset metadata probe endpoint."""

        return self.get_json("/metadata", request_id=request_id)

    def metrics(self, request_id: str | None = None) -> AxServicesResponse:
        """Call the sidecar metrics endpoint."""

        return self.get_json("/metrics", request_id=request_id)

    def get_json(
        self,
        path: str,
        *,
        request_id: str | None = None,
    ) -> AxServicesResponse:
        """Call an ax-services JSON endpoint with a GET request."""

        try:
            response = self._session.get(
                self._url(path),
                headers=self._headers(request_id),
                timeout=self._config.timeout_seconds,
            )
            return self._to_response(response)
        except requests.RequestException as ex:
            return AxServicesResponse(ok=False, status_code=None, error=str(ex))

    def post_json(
        self,
        path: str,
        payload: Mapping[str, Any],
        *,
        request_id: str | None = None,
    ) -> AxServicesResponse:
        """Call an ax-services JSON endpoint with a POST request."""

        try:
            response = self._session.post(
                self._url(path),
                json=dict(payload),
                headers=self._headers(request_id, content_type="application/json"),
                timeout=self._config.timeout_seconds,
            )
            return self._to_response(response)
        except requests.RequestException as ex:
            return AxServicesResponse(ok=False, status_code=None, error=str(ex))

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            raise ValueError("ax-services path must start with '/'")
        return f"{self._config.base_url}{path}"

    def _headers(
        self,
        request_id: str | None,
        *,
        content_type: str | None = None,
    ) -> dict[str, str]:
        headers: dict[str, str] = {}
        if request_id is not None:
            headers["x-request-id"] = request_id
        if content_type is not None:
            headers["content-type"] = content_type
        if self._config.internal_token is not None:
            headers["authorization"] = f"Bearer {self._config.internal_token}"
        return headers

    @staticmethod
    def _to_response(response: requests.Response) -> AxServicesResponse:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        return AxServicesResponse(
            ok=response.ok,
            status_code=response.status_code,
            payload=payload if isinstance(payload, dict) else None,
        )
