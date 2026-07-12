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

from sqlalchemy.exc import SQLAlchemyError

from axbi.commands.dataset.exceptions import DatasetNotFoundError
from axbi.commands.explore.permalink.base import BaseExplorePermalinkCommand
from axbi.daos.key_value import KeyValueDAO
from axbi.explore.permalink.exceptions import ExplorePermalinkGetFailedError
from axbi.explore.permalink.types import ExplorePermalinkValue
from axbi.explore.utils import check_access as check_chart_access
from axbi.key_value.exceptions import (
    KeyValueCodecDecodeException,
    KeyValueGetFailedError,
    KeyValueParseKeyError,
)
from axbi.key_value.utils import decode_permalink_id
from axbi.utils.core import DatasourceType

logger = logging.getLogger(__name__)


class GetExplorePermalinkCommand(BaseExplorePermalinkCommand):
    def __init__(self, key: str):
        self.key = key

    def run(self) -> ExplorePermalinkValue | None:
        self.validate()
        try:
            key = decode_permalink_id(self.key, salt=self.salt)
            value = KeyValueDAO.get_value(self.resource, key, self.codec)
            if value:
                chart_id: int | None = value.get("chartId")
                # keep this backward compatible for old permalinks
                datasource_id: int = (
                    value.get("datasourceId") or value.get("datasetId") or 0
                )
                datasource_type = DatasourceType(
                    value.get("datasourceType", DatasourceType.TABLE)
                )
                check_chart_access(datasource_id, chart_id, datasource_type)
                return value
            return None
        except (
            DatasetNotFoundError,
            KeyValueCodecDecodeException,
            KeyValueGetFailedError,
            KeyValueParseKeyError,
        ) as ex:
            raise ExplorePermalinkGetFailedError(message=str(ex)) from ex
        except SQLAlchemyError as ex:
            logger.exception("Error running get command")
            raise ExplorePermalinkGetFailedError() from ex

    def validate(self) -> None:
        pass
