import asyncio

import pytest

import aioudp


async def bad_server(_: aioudp.Connection) -> None:
    raise Exception


async def echo_server(connection: aioudp.Connection) -> None:
    async for data in connection:
        await connection.send(data)


async def no_server(_: aioudp.Connection) -> None:
    pass


# XXX: Binary search for optimal timeout


@pytest.mark.asyncio
async def test_bad_server():
    async with aioudp.serve(host="localhost", port=9999, handler=bad_server):
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.send(b"Hello world")
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(connection.recv(), timeout=1)


@pytest.mark.asyncio
async def test_no_send_data():
    async with aioudp.serve(host="localhost", port=9999, handler=no_server):
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.send(b"Hello world")
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(connection.recv(), timeout=1)
