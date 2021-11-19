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
        """Returns the local address of the connection. This is your IP

        .. seealso::
            :meth:`remote_address`

        Returns:
            AddrType: This is a `tuple` containing the hostname and port

        """
        return self.get_local_addr()  # type: ignore  # This is a bug https://github.com/python/mypy/issues/6910

    @property
    def remote_address(self) -> Optional[AddrType]:
        """Returns the remote address of the connection. This is their IP

        .. seealso::
            :meth:`local_address`

        Returns:
            AddrType: This is a `tuple` containing the hostname and port

        """
        return self.get_remote_addr()  # type: ignore  # See above

    async def recv(self) -> bytes:
        """Receives a message from the connection

        Returns:
            bytes: The received `bytes`.

        Raises:
            exceptions.ConnectionClosedError: The connection is closed

        """
        the_next_one = await self.recv_func()  # type: ignore  # See above
        if the_next_one is None:
            assert self.is_closing()  # type: ignore  # See above
            raise exceptions.ConnectionClosedError("The connection is closed")
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
        if self.is_closing():  # type: ignore  # See above
            raise exceptions.ConnectionClosedError("The connection is closed")
        if not data:
            raise ValueError("You must send some data")
        self.send_func(data)  # type: ignore  # See above

    def __aiter__(self) -> "Connection":
        return self

    async def __anext__(self) -> bytes:
        try:
            return await self.recv()
        except exceptions.ConnectionClosedError as error:
            raise StopAsyncIteration from error
