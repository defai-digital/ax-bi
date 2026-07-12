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
from typing import cast

from axbi import db
from axbi.commands.dataset.exceptions import DatasetNotFoundError
from axbi.commands.sql_lab.permalink.base import BaseSqlLabPermalinkCommand
from axbi.daos.key_value import KeyValueDAO
from axbi.key_value.exceptions import (
    KeyValueCodecDecodeException,
    KeyValueGetFailedError,
    KeyValueParseKeyError,
)
from axbi.key_value.utils import decode_permalink_id
from axbi.models import core as models
from axbi.sqllab.permalink.exceptions import SqlLabPermalinkGetFailedError
from axbi.sqllab.permalink.types import SqlLabPermalinkValue
from axbi.utils import core as utils

logger = logging.getLogger(__name__)


class GetSqlLabPermalinkCommand(BaseSqlLabPermalinkCommand):
    def __init__(self, key: str):
        self.key = key

    def run(self) -> SqlLabPermalinkValue | None:
        self.validate()
        if self.key.startswith("kv:"):
            id = int(self.key[3:])
            try:
                kv = db.session.query(models.KeyValue).filter_by(id=id).scalar()
                if not kv:
                    return None
                return cast(
                    SqlLabPermalinkValue,
                    self.codec.decode(kv.value.encode("utf-8")),
                )
            except Exception as ex:
                raise SqlLabPermalinkGetFailedError(
                    message=utils.error_msg_from_exception(ex)
                ) from ex

        try:
            key = decode_permalink_id(self.key, salt=self.salt)
            value = KeyValueDAO.get_value(self.resource, key, self.codec)
            if value:
                return value
            return None
        except (
            DatasetNotFoundError,
            KeyValueCodecDecodeException,
            KeyValueGetFailedError,
            KeyValueParseKeyError,
        ) as ex:
            raise SqlLabPermalinkGetFailedError(message=ex.message) from ex

    def validate(self) -> None:
        pass
