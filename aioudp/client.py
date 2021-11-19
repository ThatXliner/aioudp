import asyncio
import functools
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, NoReturn, Optional

from aioudp import connection


@dataclass
class ClientProtocol(asyncio.DatagramProtocol):
    msg_queue: "asyncio.Queue[Optional[bytes]]"
    transport: Optional[asyncio.BaseTransport] = None

    # def connection_made(self, transport: "asyncio.BaseTransport") -> None:
    #     self.transport = transport

    def datagram_received(self, data: bytes, _: connection.AddrType) -> None:
        self.msg_queue.put_nowait(data)

    def error_received(self, exc: Exception) -> NoReturn:
        # Haven't figured out why this can happen
        raise exc

    def connection_lost(self, exc: Optional[Exception]) -> None:
        # Haven't figured out why this can happen
        if exc is not None:
            raise exc
        self.msg_queue.put_nowait(None)


@asynccontextmanager
async def connect(host: str, port: int) -> AsyncIterator[connection.Connection]:
    """Connects to a UDP server.

    .. seealso::

        :func:`serve`

    Args:
        host (str): The server's host name/address
        port (int): The server's port number

    """
    loop = asyncio.get_running_loop()
    msgs: "asyncio.Queue[Optional[bytes]]" = asyncio.Queue()
    transport: "asyncio.BaseTransport"
    _: "asyncio.BaseProtocol"
    transport, _ = await loop.create_datagram_endpoint(
        lambda: ClientProtocol(msgs),
        remote_addr=(host, port),
        # FIXME: Should use `local_addr` or `remote_addr` be configurable?
    )
    try:
        yield connection.Connection(  # TODO: REFACTOR: minimal args
            send_func=transport.sendto,  # type: ignore
            recv_func=msgs.get,
            is_closing=transport.is_closing,
            get_local_addr=functools.partial(transport.get_extra_info, "sockname"),
            get_remote_addr=functools.partial(transport.get_extra_info, "peername"),
        )
    finally:
        transport.close()
