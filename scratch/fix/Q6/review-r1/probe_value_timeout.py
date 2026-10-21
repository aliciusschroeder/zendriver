"""Time out only exp.value, then send R1's events: does exp.response / body resolve to R1?
Also: burst of all six events in a single dispatch."""

import asyncio
import sys
from typing import Any

import zendriver as zd
from zendriver.core.connection import Connection
from zendriver.core.expect import RequestExpectation

sys.path.insert(0, "/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-17")
from tests.core.test_expect import (  # noqa: E402
    IMAGE_PATTERN,
    dispatch,
    loading_finished,
    request_will_be_sent,
    response_received,
)


async def main() -> None:
    print("zendriver:", zd.__file__, sys.version.split()[0])
    connection = Connection("ws://unused")
    sent: list[str] = []

    async def send(cdp_obj: Any, _is_update: bool = False) -> Any:
        cmd = next(cdp_obj)
        sent.append(cmd["params"]["requestId"])
        return f"body of {cmd['params']['requestId']}", False

    connection.send = send  # type: ignore[method-assign]

    async with RequestExpectation(connection, IMAGE_PATTERN) as exp:
        try:
            await asyncio.wait_for(exp.value, 0.05)
        except asyncio.TimeoutError:
            print("value timed out; request_future cancelled:", exp.request_future.cancelled())
        results = await dispatch(
            connection,
            request_will_be_sent("R1"),
            request_will_be_sent("R2"),
            response_received("R1"),
            response_received("R2"),
            loading_finished("R1"),
            loading_finished("R2"),
        )
        print("results:", results)
        resp = await asyncio.wait_for(exp.response, 1)
        body = await asyncio.wait_for(exp.response_body, 1)
        print("request_id:", exp.request_id, "response:", resp.url, "body:", body, "sent:", sent)


asyncio.run(main())
