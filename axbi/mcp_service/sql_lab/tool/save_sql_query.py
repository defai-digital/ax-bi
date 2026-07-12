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

"""
Save SQL Query MCP Tool

Tool for saving a SQL query as a named SavedQuery in AxBI,
so it appears in SQL Lab's "Saved Queries" list and can be
reloaded/shared via URL.
"""

import logging

from axbi_core.mcp.decorators import tool, ToolAnnotations
from fastmcp import Context

from axbi.commands.query.create import CreateSavedQueryCommand
from axbi.commands.query.exceptions import (
    SavedQueryCreateFailedError,
    SavedQueryDatabaseAccessDeniedError,
    SavedQueryDatabaseNotFoundError,
)
from axbi.errors import AxBIError, AxBIErrorType, ErrorLevel
from axbi.exceptions import AxBIErrorException, AxBISecurityException
from axbi.mcp_service.sql_lab.schemas import (
    SaveSqlQueryRequest,
    SaveSqlQueryResponse,
)
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context
from axbi.mcp_service.utils.url_utils import get_axbi_base_url

logger = logging.getLogger(__name__)


@tool(
    tags=["mutate"],
    class_permission_name="SavedQuery",
    method_permission_name="write",
    annotations=ToolAnnotations(
        title="Save SQL query",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
async def save_sql_query(
    request: SaveSqlQueryRequest, ctx: Context
) -> SaveSqlQueryResponse:
    """Save a SQL query so it appears in SQL Lab's Saved Queries list.

    Creates a persistent SavedQuery that the user can reload from
    SQL Lab, share via URL, and find in the Saved Queries page.
    Requires a database_id, a label (name), and the SQL text.
    """
    await ctx.info(
        f"Saving SQL query: database_id={request.database_id}, label={request.label!r}"
    )

    try:
        with mcp_event_log_context(action="mcp.save_sql_query.create"):
            saved_query = CreateSavedQueryCommand(
                {
                    "db_id": request.database_id,
                    "label": request.label,
                    "sql": request.sql,
                    "schema": request.schema_name or "",
                    "catalog": request.catalog,
                    "description": request.description or "",
                }
            ).run()

        base_url = get_axbi_base_url()
        saved_query_url = f"{base_url}/sqllab?savedQueryId={saved_query.id}"

        await ctx.info(
            f"Saved query created: id={saved_query.id}, url={saved_query_url}"
        )

        return SaveSqlQueryResponse(
            id=saved_query.id,
            label=saved_query.label,
            sql=saved_query.sql,
            database_id=saved_query.db_id,
            schema_name=saved_query.schema or None,
            catalog=getattr(saved_query, "catalog", None),
            description=saved_query.description or None,
            url=saved_query_url,
        )

    except SavedQueryDatabaseNotFoundError as exc:
        raise AxBIErrorException(
            AxBIError(
                message=str(exc),
                error_type=AxBIErrorType.DATABASE_NOT_FOUND_ERROR,
                level=ErrorLevel.ERROR,
            )
        ) from exc
    except SavedQueryDatabaseAccessDeniedError as exc:
        raise AxBISecurityException(
            AxBIError(
                message=str(exc),
                error_type=AxBIErrorType.DATABASE_SECURITY_ACCESS_ERROR,
                level=ErrorLevel.ERROR,
            )
        ) from exc
    except SavedQueryCreateFailedError as exc:
        await ctx.error(
            "Failed to save SQL query: "
            f"database_id={request.database_id}, error_type={type(exc).__name__}"
        )
        raise
