import pytest
from hypothesis import assume, given, strategies as st

import aioudp
from aioudp import exceptions
import asyncio


async def bad_server(connection: aioudp.Connection) -> None:
    raise Exception


async def echo_server(connection: aioudp.Connection) -> None:
    async for data in connection:
        await connection.send(data)


async def reverse_echo_server(connection: aioudp.Connection) -> None:
    await connection.send(b"Hi")


async def no_server(connection: aioudp.Connection) -> None:
    pass


# XXX: Binary search for optimal timeout


@given(data=st.binary())
@pytest.mark.asyncio
async def test_bad_server(data: bytes):
    assume(data)
    async with aioudp.serve(host="localhost", port=9999, handler=bad_server):
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.send(data)
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(connection.recv(), timeout=1)


@given(data=st.binary())
@pytest.mark.asyncio
async def test_no_send_data(data: bytes):
    assume(data)
    async with aioudp.serve(host="localhost", port=9999, handler=no_server):
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.send(data)
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(connection.recv(), timeout=1)


@pytest.mark.asyncio
async def test_reverse_echo_works():
    async with aioudp.serve(host="localhost", port=9999, handler=reverse_echo_server):
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.recv() == b"Hi"
