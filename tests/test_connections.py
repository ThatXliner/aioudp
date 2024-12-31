import pytest
from hypothesis import assume, given, settings, strategies as st

import aioudp
from aioudp import exceptions


async def echo_server(connection: aioudp.Connection) -> None:
    async for data in connection:
        assert isinstance(data, bytes), data
        await connection.send(data)


async def one_time_echo_server(connection: aioudp.Connection) -> None:
    await connection.send(await connection.recv())


@given(data=st.binary())
@pytest.mark.asyncio
async def test_echo_server(data: bytes):
    assume(data)
    async with aioudp.serve(host="localhost", port=9999, handler=echo_server):
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.send(data)
            assert await connection.recv() == data


@given(data=st.binary())
@pytest.mark.asyncio
async def test_recieve_closed_connection(data: bytes):
    assume(data)
    async with aioudp.serve(host="localhost", port=9999, handler=one_time_echo_server):
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.send(data)
            assert await connection.recv() == data
        with pytest.raises(exceptions.ConnectionClosedError):
            await connection.recv()


@given(data=st.binary(), extra_data=st.binary())
@settings(deadline=None)
@pytest.mark.asyncio
async def test_send_closed_connection(data: bytes, extra_data: bytes):
    assume(data)
    async with aioudp.serve(host="localhost", port=9999, handler=one_time_echo_server):
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.send(data)
            assert await connection.recv() == data
        with pytest.raises(exceptions.ConnectionClosedError):
            await connection.send(extra_data)


@given(data=st.binary())
@pytest.mark.asyncio
async def test_addresses(data: bytes):
    assume(data)
    async with aioudp.serve(host="localhost", port=9999, handler=one_time_echo_server):
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.send(data)
            assert await connection.recv() == data
            assert connection.local_address[1] != 9999
            assert connection.remote_address[1] == 9999


@pytest.mark.asyncio
async def test_empty_data():
    async with aioudp.serve(host="localhost", port=9999, handler=one_time_echo_server):
        async with aioudp.connect("localhost", 9999) as connection:
            with pytest.raises(ValueError):
                await connection.send(b"")
