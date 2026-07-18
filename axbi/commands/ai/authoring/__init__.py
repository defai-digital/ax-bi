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
"""Transport-neutral application contracts for analytics authoring."""

from axbi.commands.ai.authoring.capabilities import (
    GetAuthoringCapabilitiesCommand,
)
from axbi.commands.ai.authoring.confidence import (
    DEFAULT_MIN_PLAN_CONFIDENCE,
    evaluate_compose_gate,
)
from axbi.commands.ai.authoring.context import AuthoringContext
from axbi.commands.ai.authoring.contracts import (
    ArtifactRef,
    AuthoringCapabilities,
    AuthoringError,
    AuthoringLimits,
    AuthoringOutcome,
    AuthoringWarning,
)
from axbi.commands.ai.authoring.errors import AuthoringCommandError

__all__ = [
    "ArtifactRef",
    "AuthoringCapabilities",
    "AuthoringCommandError",
    "AuthoringContext",
    "AuthoringError",
    "AuthoringLimits",
    "AuthoringOutcome",
    "AuthoringWarning",
    "DEFAULT_MIN_PLAN_CONFIDENCE",
    "GetAuthoringCapabilitiesCommand",
    "evaluate_compose_gate",
]
