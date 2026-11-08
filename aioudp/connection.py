"""Connection class for aioudp."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Tuple

from aioudp import exceptions

__all__ = ["Connection"]

AddrType = Tuple[str, int]

_PROACTOR_LOOP: type | tuple[()] = getattr(asyncio, "ProactorEventLoop", ())


class _Inbox:
    def __init__(self, queue_size: int | None) -> None:
        self._queue: asyncio.Queue[bytes | Exception] = asyncio.Queue(queue_size or 0)
        self.closed = False

    def put(self, item: bytes | Exception) -> None:
        with contextlib.suppress(asyncio.QueueFull):
            self._queue.put_nowait(item)

    def close(self) -> None:
        self.closed = True
        while not self._queue.empty():
            self._queue.get_nowait()
        self._queue.put_nowait(exceptions.ConnectionClosedError())

    async def get(self) -> bytes:
        item = await self._queue.get()
        if isinstance(item, exceptions.ConnectionClosedError):
            self._queue.put_nowait(item)
            raise exceptions.ConnectionClosedError
        if isinstance(item, Exception):
            raise item
        return item


class _Endpoint(asyncio.DatagramProtocol):
    transport: asyncio.DatagramTransport
    sending = False

    def connection_made(
        self,
        transport: asyncio.DatagramTransport,  # type: ignore[override]
    ) -> None:
        self.transport = transport

    def sendto(self, data: bytes, addr: AddrType | None) -> None:
        self.sending = True
        try:
            self.transport.sendto(data, addr)
        finally:
            self.sending = False

    def close(self) -> None:
        self.transport.close()
        # CPython's proactor transport never calls connection_lost when close()
        # lands while a send is in flight, and drops queued sends either way.
        if isinstance(asyncio.get_running_loop(), _PROACTOR_LOOP):
            self.transport.abort()

    def error_received(self, exc: Exception) -> None:
        # The transport reports a failed send synchronously from inside sendto.
        if self.sending:
            raise exc
        self.socket_error(exc)

    def socket_error(self, exc: Exception) -> None:
        raise NotImplementedError


class Connection:
    """Represents a server-client connection. Do not instantiate manually."""

    def __init__(
        self,
        endpoint: _Endpoint,
        inbox: _Inbox,
        peer: AddrType | None,
    ) -> None:
        """Connect to ``peer``, or to the endpoint's own peer if it is None."""
        self._endpoint = endpoint
        self._inbox = inbox
        self._peer = peer

    @property
    def local_address(self) -> AddrType:
        """Returns the local address of the connection. This is your IP.

        .. seealso::
            :meth:`remote_address`

        Returns:
            tuple[str, int]: This is a `tuple` containing the hostname and port

        """
        address: AddrType = self._endpoint.transport.get_extra_info("sockname")
        return address

    @property
    def remote_address(self) -> AddrType:
        """Returns the remote address of the connection. This is their IP.

        .. seealso::
            :meth:`local_address`

        Returns:
            tuple[str, int]: This is a `tuple` containing the hostname and port

        """
        if self._peer is not None:
            return self._peer
        address: AddrType = self._endpoint.transport.get_extra_info("peername")
        return address

    async def recv(self) -> bytes:
        """Receives a message from the connection.

        A client connection closes when :func:`~aioudp.connect` exits.
        A server connection closes when its handler returns
        or when :func:`~aioudp.serve` exits.
        Once the connection is closed, every call raises
        :class:`~aioudp.exceptions.ConnectionClosedError`
        and messages that were still queued are dropped.

        Returns:
            bytes: The received `bytes`.

        Raises:
            exceptions.ConnectionClosedError: The connection is closed
            OSError: The socket reported an error, such as
                :class:`ConnectionRefusedError` when nothing listens on the
                server's port. Only client connections raise this.

        """
        return await self._inbox.get()

    async def send(self, data: bytes) -> None:
        """Send a message to the connection.

        The reason why this send function is `async` is due to API consistency.
        There is actually no underlying `async` call so feel free to
        just forgo the `await`.

        .. warning::
            Since this is UDP, there is no guarantee that the message will be sent

        Args:
            data (bytes): The message in bytes to send

        Raises:
            exceptions.ConnectionClosedError: The connection is closed
            ValueError: There is no data to send
            OSError: The socket rejected the message, for example because it
                is too large. On Windows' default event loop, sends finish in
                the background, so a client gets this error from a later
                :meth:`recv` and a server logs it instead.

        """
        if self._inbox.closed or self._endpoint.transport.is_closing():
            msg = "The connection is closed"
            raise exceptions.ConnectionClosedError(msg)
        if not data:
            msg = "You must send some data"
            raise ValueError(msg)
        self._endpoint.sendto(data, self._peer)

    def __aiter__(self) -> Connection:
        """Return an async iterator of messages received."""
        return self

    async def __anext__(self) -> bytes:
        """Get the next message received. Functionally equivalent to :meth:`recv`."""
        try:
            return await self.recv()
        except exceptions.ConnectionClosedError as error:
            raise StopAsyncIteration from error
