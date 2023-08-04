"""Code related both client-side or server-side connections."""
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Tuple

from aioudp import exceptions

__all__ = ["Connection"]

AddrType = Tuple[str, int]


@dataclass
class Connection:  # TODO: REFACTOR: minimal args
    """Represents a server-client connection. Do not instantiate manually."""

    send_func: Callable[[bytes], None]
    recv_func: Callable[[], Awaitable[Optional[bytes]]]
    is_closing: Callable[[], bool]
    get_local_addr: Callable[[], AddrType]
    get_remote_addr: Callable[[], Optional[AddrType]]
    closed: bool = False

    @property
    def local_address(self) -> AddrType:
        """The local address and port of the connection.

        The address should your local IP address (within the LAN).

        .. seealso::
            :attr:`remote_address`

        Returns:
            Tuple[str, int]: This is a `tuple` containing the hostname and port

        """
        return self.get_local_addr()

    @property
    def remote_address(self) -> Optional[AddrType]:
        """The remote address and port of the connection.

        The address should be their IP, which
        should be their router's public server address.

        .. seealso::
            :attr:`local_address`

        Returns:
            Tuple[str, int]: This is a `tuple` containing the hostname and port

        """
        return self.get_remote_addr()

    async def recv(self) -> bytes:
        """Receive a message from the connection.

        It is named this way since ``recv`` is a shorthand for "receive".

        Returns:
            bytes: The received `bytes`.

        Raises:
            exceptions.ConnectionClosedError: The connection is closed

        """
        the_next_one = await self.recv_func()
        if the_next_one is None:
            assert self.is_closing()
            msg = "The connection is closed"
            raise exceptions.ConnectionClosedError(msg)
        return the_next_one

    async def send(self, data: bytes) -> None:
        """Sends a message to the connection.

        .. warning::
            Since this is UDP, there is no guarantee that the message will be sent

        Args:
            data (bytes): The message in bytes to send

        Raises:
            exceptions.ConnectionClosedError: The connection is closed
            ValueError: There is no data to send
        """
        if self.is_closing():  # See above
            msg = "The connection is closed"
            raise exceptions.ConnectionClosedError(msg)
        if not data:
            msg = "You must send some data"
            raise ValueError(msg)
        self.send_func(data)  # See above

    def __aiter__(self) -> "Connection":
        """Returns itself since it also implements __anext__."""
        return self

    async def __anext__(self) -> bytes:
        """Receive messages in this connection.

        Iterating through a connection is the same
        as calling :meth:`recv` in a loop.
        """
        try:
            return await self.recv()
        except exceptions.ConnectionClosedError as error:
            raise StopAsyncIteration from error
