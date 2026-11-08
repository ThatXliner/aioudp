"""Server-side UDP connection."""

from __future__ import annotations

import asyncio
import functools
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Coroutine

from aioudp import connection
from aioudp.connection import _Endpoint, _Inbox

logger = logging.getLogger(__name__)


class _ServerProtocol(_Endpoint):
    def __init__(
        self,
        handler: Callable[[connection.Connection], Coroutine[Any, Any, None]],
        queue_size: int | None,
    ) -> None:
        self.handler = handler
        self.queue_size = queue_size
        self.inboxes: dict[connection.AddrType, _Inbox] = {}
        self.tasks: set[asyncio.Task[None]] = set()

    def datagram_received(self, data: bytes, addr: connection.AddrType) -> None:
        if addr not in self.inboxes:
            inbox = self.inboxes[addr] = _Inbox(self.queue_size)
            task = asyncio.create_task(
                self.handler(connection.Connection(self, inbox, addr)),
            )
            self.tasks.add(task)
            task.add_done_callback(functools.partial(self.handler_done, addr))
        self.inboxes[addr].put(data)

    def handler_done(self, addr: connection.AddrType, task: asyncio.Task[None]) -> None:
        self.inboxes.pop(addr).close()
        self.tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            task.get_loop().call_exception_handler(
                {
                    "message": f"aioudp handler for {addr} raised",
                    "exception": task.exception(),
                    "task": task,
                },
            )

    def socket_error(self, exc: Exception) -> None:
        logger.warning("Socket error on the server", exc_info=exc)

    def connection_lost(self, _exc: Exception | None) -> None:
        for inbox in self.inboxes.values():
            inbox.close()


@asynccontextmanager
async def serve(
    host: str,
    port: int,
    handler: Callable[[connection.Connection], Coroutine[Any, Any, None]],
    queue_size: int | None = None,
    **kwargs: Any,  # noqa: ANN401
) -> AsyncIterator[None]:
    """Run a UDP server.

    See the docs for an example UDP echo server

    The first message from a new address starts ``handler`` with a new
    :class:`~aioudp.Connection`. That connection closes when ``handler``
    returns, and the next message from the same address starts a new one.
    If ``handler`` raises, the event loop's exception handler reports it.
    When the server stops, it cancels the handlers that are still running
    and waits for them to finish.

    See Also:
        :func:`connect`

        :doc:`An example UDP echo server </index>`

    Args:
        host (str): The host name/address to run the server on
        port (int): The port number to run the server on
        handler (Callable[[connection.Connection], Awaitable[None]]):
            An asynchronous function to handle a request
            It should accept an instance of :class:`connection.Connection`
            and doesn't need to return anything.

        queue_size (int | None):
            The maximum size of the message queue used internally.
            Defaults to None, meaning an unlimited size.
            When the queue is full, new messages are dropped.
            Unless you know for sure what you're doing,
            there is no need to change this value.
        **kwargs:
            Additional keyword arguments to pass to

            `loop.create_datagram_endpoint <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint>`_.

    """
    loop = asyncio.get_running_loop()
    _, protocol = await loop.create_datagram_endpoint(
        lambda: _ServerProtocol(handler, queue_size),
        local_addr=(host, port),
        **kwargs,
    )
    try:
        yield
    finally:
        protocol.close()
        for task in protocol.tasks:
            task.cancel()
        await asyncio.gather(*protocol.tasks, return_exceptions=True)
