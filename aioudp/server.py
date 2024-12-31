"""Server-side UDP connection."""

from __future__ import annotations

import asyncio
import functools
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Coroutine, NoReturn

from aioudp import connection


@dataclass
class _ServerProtocol(asyncio.DatagramProtocol):
    handler: Callable[[connection.Connection], Coroutine[Any, Any, None]]
    queue_size: int | None
    msg_queues: dict[connection.AddrType, asyncio.Queue[bytes | None]] = field(
        default_factory=dict,
    )
    msg_handlers: dict[
        connection.AddrType,
        asyncio.Task[None],
    ] = field(
        default_factory=dict,
    )
    transport: None | asyncio.transports.DatagramTransport = None

    def connection_made(
        self,
        transport: asyncio.DatagramTransport,  # type: ignore[override]
        # I am aware of the Liskov subsitution principle
        # but asyncio.DatagramProtocol had this function signature
    ) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr: connection.AddrType) -> None:
        if addr not in self.msg_queues:
            self.msg_queues[addr] = (
                asyncio.Queue()
                if self.queue_size is None
                else asyncio.Queue(self.queue_size)
            )
            assert self.transport is not None

            def done(_) -> None:  # type: ignore[no-untyped-def]  # noqa: ANN001
                del self.msg_queues[addr]
                del self.msg_handlers[addr]

            # Strong reference is needed
            self.msg_handlers[addr] = asyncio.create_task(
                self.handler(  # See connnection.py
                    connection.Connection(  # TODO(ThatXliner): REFACTOR: minimal args
                        # https://github.com/ThatXliner/aioudp/issues/15
                        send_func=functools.partial(self.transport.sendto, addr=addr),
                        recv_func=self.msg_queues[addr].get,
                        is_closing=self.transport.is_closing,
                        get_local_addr=functools.partial(
                            self.transport.get_extra_info,
                            "sockname",
                        ),
                        # This should theoretically be
                        # the same as the `addr` parameter
                        get_remote_addr=functools.partial(
                            self.transport.get_extra_info,
                            "peername",
                        ),
                    ),
                ),
            )
            self.msg_handlers[addr].add_done_callback(done)

        self.msg_queues[addr].put_nowait(data)

    def error_received(self, exc: Exception) -> NoReturn:
        # Haven't figured out why this can happen
        raise exc

    # The server is done
    def connection_lost(self, exc: None | Exception) -> None:
        for key in self.msg_queues:
            self.msg_queues[key].put_nowait(None)
            self.msg_handlers[key].cancel()
        # Haven't figured out why this can happen
        if exc is not None:
            raise exc


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
            Defaults to None, meaning an unlimited size. Unless you know for sure
            what you're doing, there is no need to change this value.
        **kwargs:
            Additional keyword arguments to pass to
            :func:`asyncio.loop.create_datagram_endpoint`.

    """
    loop = asyncio.get_running_loop()
    transport: asyncio.BaseTransport
    _: asyncio.BaseProtocol
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _ServerProtocol(handler, queue_size),
        local_addr=(host, port),
        **kwargs,
    )
    try:
        yield
    finally:
        transport.close()
