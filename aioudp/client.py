"""Client-side UDP connection."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator

from aioudp import connection

ngr = 0


@dataclass
class _ClientProtocol(asyncio.DatagramProtocol):
    on_connection: asyncio.Future[connection.Connection]
    on_connection_lost: asyncio.Future[bool]
    msg_queue: asyncio.Queue[bytes] = field(default_factory=asyncio.Queue)

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
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

    def connection_lost(self, exc: BaseException) -> None:
        self.msg_queue.shutdown(immediate=True)
        self.on_connection_lost.set_result(True)
        if exc:
            raise exc


@asynccontextmanager
async def connect(host: str, port: int) -> AsyncIterator[connection.Connection]:
    """Connect to a UDP server.

    See Also:
    --------
        :func:`serve`

    Args:
    ----
        host (str): The server's host name/address.
        port (int): The server's port number.

    Returns:
    -------
        An asynchronous iterator yielding a connection to the UDP server.

    """
    loop = asyncio.get_running_loop()
    on_connection = loop.create_future()
    on_connection_lost = loop.create_future()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _ClientProtocol(on_connection, on_connection_lost),
        remote_addr=(host, port),
    )

    conn = await on_connection
    try:
        yield conn
    finally:
        transport.close()
        await on_connection_lost
