"""Connection class for aioudp."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Tuple

from aioudp import exceptions

__all__ = ["Connection"]

AddrType = Tuple[str, int]


@dataclass
class Connection:  # TODO(ThatXliner): REFACTOR: minimal args
    # https://github.com/ThatXliner/aioudp/issues/15
    """Represents a server-client connection. Do not instantiate manually."""

    send_func: Callable[[bytes], None]
    recv_func: Callable[[], Awaitable[bytes]]
    is_closing: Callable[[], bool]
    get_local_addr: Callable[[], AddrType]
    get_remote_addr: Callable[[], None | AddrType]
    closed: bool = False

    @property
    def local_address(self) -> AddrType:
        """Returns the local address of the connection. This is your IP.

        .. seealso::
            :meth:`remote_address`

        Returns:
            tuple[str, int]: This is a `tuple` containing the hostname and port

        """
        return self.get_local_addr()

    @property
    def remote_address(self) -> None | AddrType:
        """Returns the remote address of the connection. This is their IP.

        .. seealso::
            :meth:`local_address`

        Returns:
            tuple[str, int]: This is a `tuple` containing the hostname and port

        """
        return self.get_remote_addr()

    async def recv(self) -> bytes:
        """Receives a message from the connection.

        Returns:
            bytes: The received `bytes`.

        Raises:
            exceptions.ConnectionClosedError: The connection is closed

        """
        try:
            return await self.recv_func()
        except asyncio.QueueShutDown:
            raise exceptions.ConnectionClosedError  # noqa: B904

    async def send(self, data: bytes) -> None:
        """Send a message to the connection.

        .. warning::
            Since this is UDP, there is no guarantee that the message will be sent

        Args:
            data (bytes): The message in bytes to send

        Raises:
            exceptions.ConnectionClosedError: The connection is closed
            ValueError: There is no data to send

        """
        if self.is_closing():
            msg = "The connection is closed"
            raise exceptions.ConnectionClosedError(msg)
        if not data:
            msg = "You must send some data"
            raise ValueError(msg)
        self.send_func(data)

    def __aiter__(self) -> Connection:
        """Return an async iterator of messages received."""
        return self

    async def __anext__(self) -> bytes:
        """Get the next message received. Functionally equivalent to :meth:`recv`."""
        try:
            return await self.recv()
        except exceptions.ConnectionClosedError as error:
            raise StopAsyncIteration from error
