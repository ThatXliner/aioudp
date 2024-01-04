"""Client-side UDP connection."""
from __future__ import annotations

import asyncio
import functools
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, NoReturn

from aioudp import connection


@dataclass
class _ClientProtocol(asyncio.DatagramProtocol):
    msg_queue: asyncio.Queue[None | bytes]

    def datagram_received(self, data: bytes, _: connection.AddrType) -> None:
        self.msg_queue.put_nowait(data)

    def error_received(self, exc: Exception) -> NoReturn:
        # Haven't figured out why this can happen
        raise exc

    def connection_lost(self, exc: None | Exception) -> None:
        # Haven't figured out why this can happen
        if exc is not None:
            raise exc
        self.msg_queue.put_nowait(None)


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
    msgs: asyncio.Queue[None | bytes] = asyncio.Queue()
    transport: asyncio.DatagramTransport
    _: _ClientProtocol
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _ClientProtocol(msgs),
        remote_addr=(host, port),
    )
    conn = connection.Connection(  # TODO(ThatXliner): REFACTOR: minimal args
        # https://github.com/ThatXliner/aioudp/issues/15
        send_func=transport.sendto,
        recv_func=msgs.get,
        is_closing=transport.is_closing,
        get_local_addr=functools.partial(transport.get_extra_info, "sockname"),
        get_remote_addr=functools.partial(transport.get_extra_info, "peername"),
    )
    try:
        # This is to make sure that the connection works
        # See https://github.com/ThatXliner/aioudp/pull/3 for more information
        await conn.send(b"trash")
        yield conn
    finally:
        transport.close()
