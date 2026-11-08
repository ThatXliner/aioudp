"""Client-side UDP connection."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from aioudp import connection
from aioudp.connection import _Endpoint, _Inbox


class _ClientProtocol(_Endpoint):
    def __init__(self, queue_size: int | None) -> None:
        self.inbox = _Inbox(queue_size)
        self.lost: asyncio.Future[None] = asyncio.get_running_loop().create_future()

    def datagram_received(self, data: bytes, _addr: connection.AddrType) -> None:
        self.inbox.put(data)

    def socket_error(self, exc: Exception) -> None:
        self.inbox.put(exc)

    def connection_lost(self, _exc: Exception | None) -> None:
        self.inbox.close()
        self.lost.set_result(None)


@asynccontextmanager
async def connect(
    host: str,
    port: int,
    queue_size: int | None = None,
    **kwargs: Any,  # noqa: ANN401
) -> AsyncIterator[connection.Connection]:
    """Connect to a UDP server.

    See Also:
        :func:`serve`

    Args:
        host (str): The server's host name/address.
        port (int): The server's port number.
        queue_size (int | None):
            The maximum size of the message queue used internally.
            Defaults to None, meaning an unlimited size.
            When the queue is full, new messages are dropped.
            Unless you know for sure what you're doing,
            there is no need to change this value.
        **kwargs:
            Additional keyword arguments to pass to

            `loop.create_datagram_endpoint <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint>`_.


    Returns:
        An asynchronous iterator yielding a connection to the UDP server.

    """
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: _ClientProtocol(queue_size),
        remote_addr=(host, port),
        **kwargs,
    )
    try:
        yield connection.Connection(protocol, protocol.inbox, None)
    finally:
        transport.close()
        await protocol.lost
