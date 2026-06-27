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
"""Flask view that serves the SPA template for the /upload/ route.

The React UploadData page is registered in the frontend router, but Flask
must serve the SPA shell first so the client-side router can take over.
"""

from flask_appbuilder import expose, has_access, permission_name

from superset.superset_typing import FlaskResponse
from superset.views.base import BaseSupersetView


class UploadDataView(BaseSupersetView):
    """Serves the SPA template for the zero-config file upload page."""

    route_base = "/upload"
    # Use the same permission class as DatabaseRestApi so any role that can
    # upload files to a database can also reach this view.
    class_permission_name = "Database"

    @expose("/", methods=("GET",))
    @has_access
    @permission_name("read")
    def index(self) -> FlaskResponse:
        """Render the upload page SPA entry point."""
        return super().render_app_template()
