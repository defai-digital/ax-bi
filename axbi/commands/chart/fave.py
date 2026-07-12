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
from functools import partial

from axbi import security_manager
from axbi.commands.base import BaseCommand
from axbi.commands.chart.exceptions import (
    ChartAccessDeniedError,
    ChartFaveError,
    ChartNotFoundError,
)
from axbi.daos.chart import ChartDAO
from axbi.exceptions import AxBISecurityException
from axbi.models.slice import Slice
from axbi.utils.decorators import on_error, transaction

logger = logging.getLogger(__name__)


class AddFavoriteChartCommand(BaseCommand):
    def __init__(self, chart_id: int) -> None:
        self._chart_id = chart_id
        self._chart: Slice | None = None

    @transaction(on_error=partial(on_error, reraise=ChartFaveError))
    def run(self) -> None:
        self.validate()
        if self._chart:
            ChartDAO.add_favorite(self._chart)

    def validate(self) -> None:
        chart = ChartDAO.find_by_id(self._chart_id)
        if not chart:
            raise ChartNotFoundError()
        try:
            security_manager.raise_for_access(chart=chart)
        except AxBISecurityException as ex:
            raise ChartAccessDeniedError() from ex
        self._chart = chart
