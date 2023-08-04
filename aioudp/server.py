"""Code related to server-side connections."""
import asyncio
import functools
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator, Awaitable, Callable, Dict, NoReturn, Optional

from aioudp import connection

AsyncConnectionHandlerType = Callable[[connection.Connection], Awaitable[None]]


@dataclass
class _ServerProtocol(asyncio.DatagramProtocol):
    handler: AsyncConnectionHandlerType
    msg_handler: Dict[connection.AddrType, "asyncio.Queue[Optional[bytes]]"] = field(
        default_factory=dict,
    )
    transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: "asyncio.BaseTransport") -> None:
        assert isinstance(transport, asyncio.DatagramTransport)
        self.transport = transport

    def datagram_received(self, data: bytes, addr: connection.AddrType) -> None:
        if addr not in self.msg_handler:
            self.msg_handler[addr] = asyncio.Queue()
            assert self.transport is not None
            asyncio.create_task(
                self.handler(  # type: ignore[arg-type]  # See connnection.py
                    connection.Connection(  # TODO: REFACTOR: minimal args
                        send_func=functools.partial(self.transport.sendto, addr=addr),
                        recv_func=self.msg_handler[addr].get,
                        is_closing=self.transport.is_closing,
                        get_local_addr=functools.partial(
                            self.transport.get_extra_info,
                            "sockname",
                        ),
                        get_remote_addr=lambda: addr,
                    ),
                ),
            ).add_done_callback(lambda _: self.msg_handler.pop(addr, None))
        self.msg_handler[addr].put_nowait(data)

    def error_received(self, exc: Exception) -> NoReturn:
        # Haven't figured out why this can happen
        raise exc

    def connection_lost(self, exc: Optional[Exception]) -> None:
        # Haven't figured out why this can happen
        if exc is not None:
            raise exc
        for key in self.msg_handler:
            self.msg_handler[key].put_nowait(None)


@asynccontextmanager
async def serve(
    host: str,
    port: int,
    handler: Callable[[connection.Connection], Awaitable[None]],
) -> AsyncIterator[None]:
    """Runs a UDP server.

    See the docs for an example UDP echo server

    .. seealso::

        :func:`connect`

        :doc:`An example UDP echo server </index>`

    Args:
        host (str): The host name/address to run the server on
        port (int): The port number to run the server on
        handler (AsyncConnectionHandlerType): An async connection handler
            It should accept an instance of :class:`connection.Connection`
            and doesn't need to return anything.

    """
    loop = asyncio.get_running_loop()
    transport: "asyncio.BaseTransport"
    _: "asyncio.BaseProtocol"
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _ServerProtocol(handler),
        local_addr=(host, port),
    )
    try:
        yield
    finally:
        transport.close()
