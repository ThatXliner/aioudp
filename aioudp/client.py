"""Client-side UDP connection."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from aioudp import connection


class _ClientProtocol(asyncio.DatagramProtocol):
    def __init__(
        self,
        on_connection: asyncio.Future[connection.Connection],
        on_connection_lost: asyncio.Future[bool],
        queue_size: int | None = None,
    ) -> None:
        self.on_connection = on_connection
        self.on_connection_lost = on_connection_lost
        self.msg_queue: asyncio.Queue[bytes | None] = (
            asyncio.Queue() if queue_size is None else asyncio.Queue(queue_size)
        )

    def connection_made(
        self,
        transport: asyncio.DatagramTransport,  # type: ignore[override]
        # I am aware of the Liskov subsitution principle
        # but asyncio.DatagramProtocol had this function signature
    ) -> None:
        self.on_connection.set_result(
            connection.Connection(
                send_func=transport.sendto,
                recv_func=self.msg_queue.get,
                is_closing=transport.is_closing,
                get_local_addr=lambda: transport.get_extra_info("sockname"),
                get_remote_addr=lambda: transport.get_extra_info("peername"),
            ),
        )

    def datagram_received(self, data: bytes, _addr: connection.AddrType) -> None:
        self.msg_queue.put_nowait(data)

    def error_received(self, exc: BaseException) -> None:
        raise exc

    def connection_lost(self, exc: Exception | None) -> None:
        self.msg_queue.put_nowait(None)
        self.on_connection_lost.set_result(True)
        if exc:
            raise exc


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
            Defaults to None, meaning an unlimited size. Unless you know for sure
            what you're doing, there is no need to change this value.
        **kwargs:
            Additional keyword arguments to pass to

            `loop.create_datagram_endpoint <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint>`_.


    Returns:
        An asynchronous iterator yielding a connection to the UDP server.

    """
    loop = asyncio.get_running_loop()
    on_connection = loop.create_future()
    on_connection_lost = loop.create_future()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _ClientProtocol(on_connection, on_connection_lost, queue_size),
        remote_addr=(host, port),
        **kwargs,
    )

    conn = await on_connection
    try:
        yield conn
    finally:
        transport.close()
        await on_connection_lost
