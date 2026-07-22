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

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, ParamSpec, TYPE_CHECKING, TypeVar

from axbi_core.tasks.types import TaskContext, TaskScope

if TYPE_CHECKING:
    from axbi_core.tasks.models import Task

P = ParamSpec("P")
R = TypeVar("R")


def task(
    func: Callable[P, R] | None = None,
    /,
    *,
    name: str | None = None,
    scope: TaskScope = TaskScope.PRIVATE,
    timeout: int | None = None,
) -> Callable[[Callable[P, R]], TaskWrapper[P]] | TaskWrapper[P]:
    """
    Decorator to register a task.

    Host implementations will replace this function during initialization
    with a concrete implementation providing actual functionality.

    Supports bare usage and factory usage:

        @task
        def my_task(): ...

        @task()
        def my_task(): ...

        @task(name="generate_report", scope=TaskScope.SHARED)
        def my_task(): ...

    :param func: Function to decorate when used as ``@task`` (bare).
    :param name: Optional unique task name (e.g., "axbi.generate_thumbnail").
                 If not provided, uses the function name as the task name.
    :param scope: Task scope (TaskScope.PRIVATE, SHARED, or SYSTEM).
                  Defaults to TaskScope.PRIVATE.
    :param timeout: Optional timeout in seconds. When the timeout is reached,
                    abort handlers are triggered if registered. Can be overridden
                    at call time via TaskOptions(timeout=...).
    :returns: TaskWrapper (bare ``@task``) or a decorator factory (``@task()``).

    Note:
        Both direct calls and .schedule() return Task, regardless of the
        original function's return type. The decorated function's return value
        is discarded; only side effects and context updates matter.

    Example:
        from axbi_core.tasks.decorators import task, get_context
        from axbi_core.tasks.types import TaskScope

        # Private task (default scope) — bare decorator
        @task
        def generate_thumbnail(chart_id: int) -> None:
            ctx = get_context()
            # ... task implementation

        # Equivalent with parentheses
        @task()
        def generate_thumbnail_alt(chart_id: int) -> None:
            ctx = get_context()

        # Named task with shared scope
        @task(name="generate_report", scope=TaskScope.SHARED)
        def generate_chart_thumbnail(chart_id: int) -> None:
            ctx = get_context()

            # Update progress and payload atomically
            ctx.update_task(
                progress=0.5,
                payload={"chart_id": chart_id, "status": "processing"}
            )
            # ... task implementation

            ctx.update_task(progress=1.0)

        # System task (admin-only)
        @task(scope=TaskScope.SYSTEM)
        def cleanup_old_data() -> None:
            ctx = get_context()
            # ... cleanup implementation

        # Task with timeout
        @task(timeout=300)  # 5-minute timeout
        def long_running_task() -> None:
            ctx = get_context()

            @ctx.on_abort
            def handle_abort():
                # Called when timeout or manual abort
                pass

        # Schedule async execution
        task = generate_chart_thumbnail.schedule(chart_id=123)  # Returns Task

        # Direct call for sync execution (blocks until task is complete)
        task = generate_chart_thumbnail(chart_id=123)  # Also returns Task
    """
    # Signature matches the host replacement (axbi.tasks.decorators.task):
    # bare @task and @task(...) both work. The stub body is replaced at init.
    if func is not None and not callable(func):
        raise TypeError("task decorator first positional argument must be callable")
    raise NotImplementedError("Function will be replaced during initialization")


class TaskWrapper(Generic[P]):
    """
    Type stub for task wrapper returned by @task decorator.

    Both __call__ and .schedule() return Task.
    """

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Task:
        """Execute the task synchronously."""
        raise NotImplementedError("Will be replaced during initialization")

    def schedule(self, *args: P.args, **kwargs: P.kwargs) -> Task:
        """Schedule the task for async execution."""
        raise NotImplementedError("Will be replaced during initialization")


def get_context() -> TaskContext:
    """
    Get the current task context from ambient context.

    Host implementations will replace this function during initialization
    with a concrete implementation providing actual functionality.

    This function provides ambient access to the task context without
    requiring it to be passed as a parameter. It can only be called
    from within an async task execution.

    :returns: The current TaskContext
    :raises RuntimeError: If called outside a task execution context

    Example:
        @task("thumbnail_generation")
        def generate_chart_thumbnail(chart_id: int):
            ctx = get_context()  # Access ambient context

            # Update task state - no need to fetch task object
            ctx.update_task(
                progress=0.5,
                payload={"chart_id": chart_id}
            )
    """
    raise NotImplementedError("Function will be replaced during initialization")


__all__ = [
    "task",
    "get_context",
]
