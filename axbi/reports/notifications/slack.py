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

import backoff
from flask import g
from slack_sdk.errors import (
    BotUserAccessError,
    SlackApiError,
    SlackClientConfigurationError,
    SlackClientError,
    SlackClientNotConnectedError,
    SlackObjectFormationError,
    SlackRequestError,
    SlackTokenRotationError,
)

from axbi.reports.models import ReportRecipientType
from axbi.reports.notifications.base import (
    BaseNotification,
    get_recipient_config_target,
)
from axbi.reports.notifications.exceptions import (
    NotificationAuthorizationException,
    NotificationMalformedException,
    NotificationParamException,
    NotificationUnprocessableException,
    SlackV1NotificationError,
)
from axbi.reports.notifications.slack_mixin import SlackMixin
from axbi.utils.core import recipients_string_to_list
from axbi.utils.decorators import statsd_gauge
from axbi.utils.slack import (
    get_slack_client,
    should_use_v2_api,
)

logger = logging.getLogger(__name__)


# TODO: Deprecated: Remove this class in AxBI 6.0.0
class SlackNotification(SlackMixin, BaseNotification):  # pylint: disable=too-few-public-methods
    """
    Sends a slack notification for a report recipient
    """

    type = ReportRecipientType.SLACK

    def _get_channel(self) -> str:
        """
        Get the recipient's channel(s).
        Note Slack SDK uses "channel" to refer to one or more
        channels. Multiple channels are demarcated by a comma.
        :returns: The comma separated list of channel(s)
        """
        recipient_str = get_recipient_config_target(
            self._recipient.recipient_config_json,
            "Slack channel is required",
            allow_empty=True,
        )

        return ",".join(recipients_string_to_list(recipient_str))

    @backoff.on_exception(backoff.expo, SlackApiError, factor=10, base=2, max_tries=5)
    @statsd_gauge("reports.slack.send")
    def send(self) -> None:
        file_type, files = self._get_inline_files()
        title = self._content.name
        body = self._get_body(content=self._content)
        global_logs_context = getattr(g, "logs_context", {}) or {}

        # see if the v2 api will work
        if should_use_v2_api():
            # if we can fetch channels, then raise an error and use the v2 api
            raise SlackV1NotificationError

        try:
            client = get_slack_client()
            channel = self._get_channel()
            # files_upload returns SlackResponse as we run it in sync mode.
            if files:
                for file in files:
                    client.files_upload(
                        channels=channel,
                        file=file,
                        initial_comment=body,
                        title=title,
                        filetype=file_type,
                    )
            else:
                client.chat_postMessage(channel=channel, text=body)
            logger.info(
                "Report sent to slack",
                extra={
                    "execution_id": global_logs_context.get("execution_id"),
                },
            )
        except (
            BotUserAccessError,
            SlackRequestError,
            SlackClientConfigurationError,
        ) as ex:
            raise NotificationParamException(str(ex)) from ex
        except SlackObjectFormationError as ex:
            raise NotificationMalformedException(str(ex)) from ex
        except SlackTokenRotationError as ex:
            raise NotificationAuthorizationException(str(ex)) from ex
        except (SlackClientNotConnectedError, SlackApiError) as ex:
            raise NotificationUnprocessableException(str(ex)) from ex
        except SlackClientError as ex:
            # this is the base class for all slack client errors
            # keep it last so that it doesn't interfere with @backoff
            raise NotificationUnprocessableException(str(ex)) from ex
