import asyncio
import functools
import logging

import pytest

import aioudp
from aioudp import exceptions

HOST = "127.0.0.1"

pytestmark = pytest.mark.asyncio


def bounded(test):
    @functools.wraps(test)
    async def wrapper(*args, **kwargs):
        await asyncio.wait_for(test(*args, **kwargs), timeout=5)

    return wrapper


def loop_errors():
    errors = []
    asyncio.get_running_loop().set_exception_handler(
        lambda _loop, context: errors.append(context),
    )
    return errors


async def forever():
    await asyncio.get_running_loop().create_future()


def error_freed_only_by_gc():
    return RuntimeError(asyncio.current_task())


async def triple_echo(connection):
    async for message in connection:
        for _ in range(3):
            await connection.send(message)


@bounded
async def test_server_remote_address_is_the_peer():
    remote = asyncio.get_running_loop().create_future()

    async def handler(connection):
        remote.set_result(connection.remote_address)

    async with aioudp.serve(HOST, 9200, handler):
        async with aioudp.connect(HOST, 9200) as connection:
            await connection.send(b"hi")
            assert await remote == connection.local_address


@bounded
async def test_client_recv_after_close_always_raises():
    async with aioudp.serve(HOST, 9201, triple_echo):
        async with aioudp.connect(HOST, 9201) as connection:
            await connection.send(b"x")
            assert await connection.recv() == b"x"
            await asyncio.sleep(0.1)
        for _ in range(3):
            with pytest.raises(exceptions.ConnectionClosedError):
                await connection.recv()
        assert [message async for message in connection] == []


@bounded
async def test_close_wakes_every_pending_recv():
    async with aioudp.connect(HOST, 9202) as connection:
        waiters = [asyncio.ensure_future(connection.recv()) for _ in range(3)]
        await asyncio.sleep(0)
    results = await asyncio.gather(*waiters, return_exceptions=True)
    assert all(isinstance(r, exceptions.ConnectionClosedError) for r in results)


@bounded
async def test_server_recv_after_close_always_raises():
    accepted = asyncio.get_running_loop().create_future()

    async def handler(connection):
        accepted.set_result(connection)
        await forever()

    async with aioudp.serve(HOST, 9203, handler):
        async with aioudp.connect(HOST, 9203) as connection:
            await connection.send(b"queued")
            server_side = await accepted
    for _ in range(3):
        with pytest.raises(exceptions.ConnectionClosedError):
            await server_side.recv()


@bounded
async def test_full_client_queue_drops_datagrams_and_closes():
    errors = loop_errors()

    async def flood(connection):
        async for message in connection:
            for _ in range(5):
                await connection.send(message)

    async with aioudp.serve(HOST, 9204, flood):
        async with aioudp.connect(HOST, 9204, queue_size=1) as connection:
            await connection.send(b"x")
            await asyncio.sleep(0.1)
            assert await connection.recv() == b"x"
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(connection.recv(), timeout=0.1)
            await connection.send(b"y")
            await asyncio.sleep(0.1)
    assert errors == []


@bounded
async def test_full_server_queue_drops_datagrams_and_closes():
    errors = loop_errors()
    received = asyncio.get_running_loop().create_future()

    async def slow(connection):
        await asyncio.sleep(0.2)
        messages = []
        while True:
            try:
                messages.append(await asyncio.wait_for(connection.recv(), 0.1))
            except asyncio.TimeoutError:
                break
        received.set_result(len(messages))
        await forever()

    async with aioudp.serve(HOST, 9205, slow, queue_size=2):
        async with aioudp.connect(HOST, 9205) as connection:
            for _ in range(5):
                await connection.send(b"x")
            assert await received == 2
            for _ in range(5):
                await connection.send(b"x")
            await asyncio.sleep(0.1)
    assert errors == []


@bounded
async def test_client_recv_raises_asynchronous_socket_errors():
    errors = loop_errors()
    async with aioudp.connect(HOST, 9206) as connection:
        pending = asyncio.ensure_future(connection.recv())
        await asyncio.sleep(0)
        await connection.send(b"nobody is listening")
        with pytest.raises(ConnectionError):
            await pending
    assert errors == []


@bounded
async def test_send_raises_synchronous_socket_errors():
    errors = loop_errors()
    server_error = asyncio.get_running_loop().create_future()

    async def handler(connection):
        try:
            await connection.send(b"x" * 70000)
        except OSError as error:
            server_error.set_result(error)

    async with aioudp.serve(HOST, 9207, handler):
        async with aioudp.connect(HOST, 9207) as connection:
            with pytest.raises(OSError):
                await connection.send(b"x" * 70000)
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(connection.recv(), timeout=0.1)
            await connection.send(b"hi")
            assert isinstance(await server_error, OSError)
    assert errors == []


@bounded
async def test_server_logs_socket_errors_and_keeps_serving(monkeypatch, caplog):
    errors = loop_errors()
    loop = asyncio.get_running_loop()
    protocols = []
    create_endpoint = loop.create_datagram_endpoint

    async def spy(*args, **kwargs):
        transport, protocol = await create_endpoint(*args, **kwargs)
        protocols.append(protocol)
        return transport, protocol

    monkeypatch.setattr(loop, "create_datagram_endpoint", spy)

    async def echo(connection):
        async for message in connection:
            await connection.send(message)

    reset = ConnectionResetError(10054, "remote host closed the connection")
    with caplog.at_level(logging.WARNING, logger="aioudp"):
        async with aioudp.serve(HOST, 9208, echo):
            protocols[0].error_received(reset)
            async with aioudp.connect(HOST, 9208) as connection:
                await connection.send(b"still serving")
                assert await connection.recv() == b"still serving"
    assert errors == []
    assert any(
        record.name.startswith("aioudp") and record.exc_info[1] is reset
        for record in caplog.records
        if record.exc_info
    )


@bounded
async def test_serve_exit_cancels_and_awaits_handlers():
    accepted = asyncio.get_running_loop().create_future()
    outcome = []

    async def handler(_connection):
        accepted.set_result(None)
        try:
            await forever()
        except asyncio.CancelledError:
            await asyncio.sleep(0.05)
            outcome.append("cleaned up")
            raise

    async with aioudp.serve(HOST, 9209, handler):
        async with aioudp.connect(HOST, 9209) as connection:
            await connection.send(b"hi")
            await accepted
    assert outcome == ["cleaned up"]


@bounded
async def test_handler_exception_is_reported_once_and_isolated():
    errors = loop_errors()

    async def handler(connection):
        message = await connection.recv()
        if message == b"boom":
            raise error_freed_only_by_gc()
        await connection.send(message)

    async with aioudp.serve(HOST, 9210, handler):
        async with aioudp.connect(HOST, 9210) as bad:
            async with aioudp.connect(HOST, 9210) as good:
                await bad.send(b"boom")
                await good.send(b"hi")
                assert await good.recv() == b"hi"
                while not errors:
                    await asyncio.sleep(0.01)
    assert len(errors) == 1
    assert isinstance(errors[0]["exception"], RuntimeError)
