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

from flask import request, Response
from flask_appbuilder import expose
from flask_appbuilder.api import safe
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.security.decorators import protect
from marshmallow.exceptions import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from axbi.cachekeys.schemas import CacheInvalidationRequestSchema
from axbi.connectors.sqla.models import SqlaTable
from axbi.extensions import cache_manager, db, event_logger, stats_logger_manager
from axbi.models.cache import CacheKey
from axbi.utils.fast_cache import delete_fast_cache
from axbi.utils.session_lifecycle import commit_session
from axbi.views.base_api import BaseAxBIModelRestApi, statsd_metrics

logger = logging.getLogger(__name__)


class CacheRestApi(BaseAxBIModelRestApi):
    datamodel = SQLAInterface(CacheKey)
    resource_name = "cachekey"
    allow_browser_login = True
    class_permission_name = "CacheRestApi"
    include_route_methods = {
        "invalidate",
    }

    openapi_spec_component_schemas = (CacheInvalidationRequestSchema,)

    @expose("/invalidate", methods=("POST",))
    @protect()
    @safe
    @statsd_metrics
    @event_logger.log_this_with_context(log_to_statsd=False)
    def invalidate(self) -> Response:  # noqa: C901
        """
        Take a list of datasources, find and invalidate the associated cache records
        and remove the database records.
        ---
        post:
          summary: Invalidate cache records and remove the database records
          description: >-
            Takes a list of datasources, finds and invalidates the associated cache
            records and removes the database records.
          requestBody:
            description: >-
              A list of datasources uuid or the tuples of database and datasource names
            required: true
            content:
              application/json:
                schema:
                  $ref: "#/components/schemas/CacheInvalidationRequestSchema"
          responses:
            201:
              description: cache was successfully invalidated
            400:
              $ref: '#/components/responses/400'
            500:
              $ref: '#/components/responses/500'
        """
        try:
            body = request.get_json(cache=True, silent=True)
            if body is None:
                return self.response_400(message="Request is incorrect")
            datasources = CacheInvalidationRequestSchema().load(body)
        except KeyError:
            return self.response_400(message="Request is incorrect")
        except ValidationError as error:
            return self.response_400(message=str(error))
        datasource_uids = set(datasources.get("datasource_uids", []))
        for ds in datasources.get("datasources", []):
            ds_obj = SqlaTable.get_datasource_by_name(
                datasource_name=ds.get("datasource_name"),
                catalog=ds.get("catalog"),
                schema=ds.get("schema"),
                database_name=ds.get("database_name"),
            )

            if ds_obj:
                datasource_uids.add(ds_obj.uid)

        # Empty input is a successful no-op (clients may POST empty lists).
        # Only reject when non-empty datasource names were provided but none resolved.
        if not datasource_uids:
            requested_names = datasources.get("datasources") or []
            if requested_names:
                return self.response_400(
                    message="No matching datasources found for cache invalidation"
                )
            return self.response(201)

        cache_key_objs = list(
            db.session.scalars(
                select(CacheKey).where(CacheKey.datasource_uid.in_(datasource_uids))
            ).all()
        )
        cache_keys = [c.cache_key for c in cache_key_objs]
        if cache_key_objs:
            all_keys_deleted = cache_manager.data_cache.delete_many(*cache_keys)
            delete_fast_cache(cache_keys)

            if not all_keys_deleted:
                # expected behavior as keys may expire and cache is not a
                # persistent storage
                logger.info(
                    "Some of the cache keys were not deleted in the list %s", cache_keys
                )

            try:
                delete_stmt = CacheKey.__table__.delete().where(  # pylint: disable=no-member
                    CacheKey.cache_key.in_(cache_keys)
                )

                db.session.execute(delete_stmt)
                commit_session(db.session, context="cachekeys.invalidate")

                stats_logger_manager.instance.gauge(
                    "invalidated_cache", len(cache_keys)
                )
                logger.info(
                    "Invalidated %s cache records for %s datasources",
                    len(cache_keys),
                    len(datasource_uids),
                )
            except SQLAlchemyError as ex:  # pragma: no cover
                db.session.rollback()  # pylint: disable=consider-using-transaction
                logger.error(ex, exc_info=True)
                return self.response_500(str(ex))
        return self.response(201)
