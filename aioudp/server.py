import asyncio
import functools
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import (  # `Never` is introduced in 3.11 but aioudp supports 3.8+
    AsyncIterator,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    NoReturn,
    Optional,
)
from typing import NoReturn as Never

from aioudp import connection


@dataclass
class ServerProtocol(asyncio.DatagramProtocol):
    handler: Callable[[connection.Connection], Coroutine[Never, Never, None]]
    msg_handler: Dict[connection.AddrType, "asyncio.Queue[Optional[bytes]]"] = field(
        default_factory=dict,
    )
    transport: Optional[asyncio.transports.DatagramTransport] = None

    def connection_made(
        self,
        transport: asyncio.transports.DatagramTransport,  # type: ignore[override]
        # I am aware of the Liskov subsitution principle
        # but asyncio.DatagramProtocol had this function signature
    ) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr: connection.AddrType) -> None:
        if addr not in self.msg_handler:
            self.msg_handler[addr] = asyncio.Queue()
            assert self.transport is not None
            asyncio.create_task(
                self.handler(  # See connnection.py
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
    """Run a UDP server.

    See the docs for an example UDP echo server

    See Also
    --------
        :func:`connect`

        :doc:`An example UDP echo server </index>`

    Args:
        host (str): The host name/address to run the server on
        port (int): The port number to run the server on
        handler (Callable[[connection.Connection], Awaitable[None]]):
            An asynchronous function to handle a request
            It should accept an instance of :class:`connection.Connection`
            and doesn't need to return anything.

    """

    async def wrap_handler(con: connection.Connection) -> None:
        await con.recv()
        return await handler(con)

    loop = asyncio.get_running_loop()
    transport: "asyncio.BaseTransport"
    _: "asyncio.BaseProtocol"
    transport, _ = await loop.create_datagram_endpoint(
        lambda: ServerProtocol(wrap_handler),
        local_addr=(host, port),
    )
    try:
        yield
    finally:
        transport.close()
