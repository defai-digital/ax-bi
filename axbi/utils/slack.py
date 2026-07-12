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
from collections.abc import Callable

from flask import current_app as app
from marshmallow import ValidationError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler

from axbi import feature_flag_manager
from axbi.exceptions import AxBIException
from axbi.extensions import cache_manager
from axbi.reports.schemas import SlackChannelSchema
from axbi.utils import cache as cache_util
from axbi.utils.backports import StrEnum
from axbi.utils.core import recipients_string_to_list

logger = logging.getLogger(__name__)


class SlackChannelTypes(StrEnum):
    PUBLIC = "public_channel"
    PRIVATE = "private_channel"


class SlackClientError(Exception):
    pass


def _matches_channel_type(
    channel: SlackChannelSchema,
    channel_type: SlackChannelTypes,
) -> bool:
    is_private = channel.get("is_private")
    if not isinstance(is_private, bool):
        return False

    if channel_type == SlackChannelTypes.PUBLIC:
        return not is_private
    if channel_type == SlackChannelTypes.PRIVATE:
        return is_private
    return False


def _matches_channel_search(
    channel: SlackChannelSchema,
    search_terms: list[str],
    exact_match: bool,
) -> bool:
    name = channel.get("name")
    channel_id = channel.get("id")
    if not isinstance(name, str) or not isinstance(channel_id, str):
        return False

    channel_values = (name.lower(), channel_id.lower())
    if exact_match:
        return any(
            search_term == channel_value
            for search_term in search_terms
            for channel_value in channel_values
        )
    return any(
        search_term in channel_value
        for search_term in search_terms
        for channel_value in channel_values
    )


def get_slack_client() -> WebClient:
    token: str = app.config["SLACK_API_TOKEN"]
    if callable(token):
        token = token()
    client = WebClient(
        token=token,
        proxy=app.config["SLACK_PROXY"],
        timeout=app.config["SLACK_API_TIMEOUT"],
    )

    max_retry_count = app.config.get("SLACK_API_RATE_LIMIT_RETRY_COUNT", 2)
    rate_limit_handler = RateLimitErrorRetryHandler(max_retry_count=max_retry_count)
    client.retry_handlers.append(rate_limit_handler)

    logger.debug("Slack client configured with %d rate limit retries", max_retry_count)

    return client


@cache_util.memoized_func(
    key="slack_conversations_list",
    cache=cache_manager.cache,
)
def get_channels() -> list[SlackChannelSchema]:
    """
    Retrieves a list of all conversations accessible by the bot
    from the Slack API, and caches results (to avoid rate limits).

    The Slack API does not provide search so to apply a search use
    get_channels_with_search instead.
    """
    client = get_slack_client()
    channel_schema = SlackChannelSchema()
    channels: list[SlackChannelSchema] = []
    extra_params = {"types": ",".join(SlackChannelTypes)}
    cursor = None
    page_count = 0

    logger.info("Starting Slack channels fetch")

    try:
        while True:
            page_count += 1

            response = client.conversations_list(
                limit=999, cursor=cursor, exclude_archived=True, **extra_params
            )
            response_data = response.data
            page_channels = response_data.get("channels", [])
            if not isinstance(page_channels, list):
                raise SlackClientError("Slack API returned malformed channels payload")

            for channel in page_channels:
                if not isinstance(channel, dict):
                    logger.warning("Skipping malformed Slack channel entry")
                    continue
                try:
                    channels.append(channel_schema.load(channel))
                except ValidationError:
                    logger.warning(
                        "Skipping malformed Slack channel entry",
                        exc_info=True,
                    )

            logger.debug(
                "Fetched page %d: %d channels (total: %d)",
                page_count,
                len(page_channels),
                len(channels),
            )

            response_metadata = response_data.get("response_metadata") or {}
            cursor = (
                response_metadata.get("next_cursor")
                if isinstance(response_metadata, dict)
                else None
            )
            if not cursor:
                break

        logger.info(
            "Successfully fetched %d Slack channels in %d pages",
            len(channels),
            page_count,
        )
        return channels
    except SlackApiError as ex:
        logger.error(
            "Failed to fetch Slack channels after %d pages: %s",
            page_count,
            str(ex),
            exc_info=True,
        )
        raise


def get_channels_with_search(
    search_string: str = "",
    types: list[SlackChannelTypes] | None = None,
    exact_match: bool = False,
    force: bool = False,
) -> list[SlackChannelSchema]:
    """
    The slack api is paginated but does not include search, so we need to fetch
    all channels and filter them ourselves
    This will search by slack name or id
    """
    try:
        channels = get_channels(
            force=force,
            cache_timeout=app.config["SLACK_CACHE_TIMEOUT"],
        )
    except SlackApiError as ex:
        # Check if it's a rate limit error
        status_code = getattr(ex.response, "status_code", None)
        if status_code == 429:
            raise AxBIException(
                f"Slack API rate limit exceeded: {ex}. "
                "For large workspaces, consider increasing "
                "SLACK_API_RATE_LIMIT_RETRY_COUNT"
            ) from ex
        raise AxBIException(f"Failed to list channels: {ex}") from ex
    except SlackClientError as ex:
        raise AxBIException(f"Failed to list channels: {ex}") from ex

    if types and len(types) != len(SlackChannelTypes):
        conditions: list[Callable[[SlackChannelSchema], bool]] = []
        if SlackChannelTypes.PUBLIC in types:
            conditions.append(
                lambda channel: _matches_channel_type(
                    channel,
                    SlackChannelTypes.PUBLIC,
                )
            )
        if SlackChannelTypes.PRIVATE in types:
            conditions.append(
                lambda channel: _matches_channel_type(
                    channel,
                    SlackChannelTypes.PRIVATE,
                )
            )

        channels = [
            channel for channel in channels if any(cond(channel) for cond in conditions)
        ]

    # The search string can be multiple channels separated by commas
    if search_string:
        search_array = [
            search.lower() for search in recipients_string_to_list(search_string)
        ]
        channels = [
            channel
            for channel in channels
            if _matches_channel_search(channel, search_array, exact_match)
        ]
    return channels


def should_use_v2_api() -> bool:
    if not feature_flag_manager.is_feature_enabled("ALERT_REPORT_SLACK_V2"):
        return False
    try:
        client = get_slack_client()
        client.conversations_list()
        logger.info("Slack API v2 is available")
        return True
    except SlackApiError:
        # use the v1 api but warn with a deprecation message
        logger.warning(
            """Your current Slack scopes are missing `channels:read`. Please add
            this to your Slack app in order to continue using the v1 API. Support
            for the old Slack API will be removed in AxBI version 6.0.0."""
        )
        return False


def get_user_avatar(email: str, client: WebClient = None) -> str:
    client = client or get_slack_client()
    try:
        response = client.users_lookupByEmail(email=email)
    except Exception as ex:
        raise SlackClientError(f"Failed to lookup user by email: {email}") from ex

    user = response.data.get("user")
    if user is None:
        raise SlackClientError("No user found with that email.")

    profile = user.get("profile")
    if profile is None:
        raise SlackClientError("User found but no profile available.")

    avatar_url = profile.get("image_192")
    if avatar_url is None:
        raise SlackClientError("Profile image is not available.")

    return avatar_url
