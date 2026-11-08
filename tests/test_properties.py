from __future__ import annotations

import asyncio
import functools
from collections import Counter
from contextlib import AsyncExitStack
from typing import Any, Awaitable, Callable, TypeVar

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    precondition,
    rule,
    run_state_machine_as_test,
)

import aioudp
from aioudp.exceptions import ConnectionClosedError

from .conftest import HOST

# macOS caps loopback datagrams at net.inet.udp.maxdgram (9216 by default);
# Linux and Windows allow 65507.
MAX_DATAGRAM = 9216
TIMEOUT = 3.0
# For calls that need no network round trip. A hang costs a full timeout on
# every shrink step, so a short one keeps a regression's report fast.
IMMEDIATE = 0.5
SMALLEST_DEFAULT_RCVBUF = 8192
MAX_STATEFUL_PAYLOAD = 1024
MAX_IN_FLIGHT = SMALLEST_DEFAULT_RCVBUF // MAX_STATEFUL_PAYLOAD
SETTLE = 0.02

T = TypeVar("T")


def bounded(test: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
    @functools.wraps(test)
    async def wrapper(*args: Any, **kwargs: Any) -> None:
        await asyncio.wait_for(test(*args, **kwargs), TIMEOUT)

    return wrapper


def record_loop_errors(loop: asyncio.AbstractEventLoop) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    loop.set_exception_handler(lambda _loop, context: errors.append(context))
    return errors


async def echo(conn: aioudp.Connection) -> None:
    async for data in conn:
        await conn.send(data)


@given(payload=st.binary(min_size=1, max_size=MAX_DATAGRAM))
@example(payload=b"\x00")
@example(payload=bytes(range(256)) * (MAX_DATAGRAM // 256))
@pytest.mark.asyncio
@bounded
async def test_echo_preserves_payload(free_port: int, payload: bytes) -> None:
    async with aioudp.serve(HOST, free_port, echo), aioudp.connect(
        HOST, free_port
    ) as conn:
        await conn.send(payload)
        assert await conn.recv() == payload


@given(schedule=st.lists(st.integers(0, 7), min_size=1, max_size=40))
@pytest.mark.asyncio
@bounded
async def test_peers_only_receive_their_own_echoes(
    free_port: int, schedule: list[int]
) -> None:
    sent: dict[int, Counter[bytes]] = {peer: Counter() for peer in set(schedule)}
    async with aioudp.serve(HOST, free_port, echo), AsyncExitStack() as stack:
        conns = {
            peer: await stack.enter_async_context(aioudp.connect(HOST, free_port))
            for peer in sent
        }
        for seq, peer in enumerate(schedule):
            payload = f"{peer}:{seq}".encode()
            await conns[peer].send(payload)
            sent[peer][payload] += 1
        for peer, conn in conns.items():
            received = Counter(
                [await conn.recv() for _ in range(sum(sent[peer].values()))],
            )
            assert received == sent[peer]


@given(peers=st.integers(1, 8))
@pytest.mark.asyncio
@bounded
async def test_server_sees_each_client_address(free_port: int, peers: int) -> None:
    seen: list[tuple[Any, Any]] = []

    async def record(conn: aioudp.Connection) -> None:
        seen.append((conn.local_address, conn.remote_address))
        await echo(conn)

    async with aioudp.serve(HOST, free_port, record), AsyncExitStack() as stack:
        clients = [
            await stack.enter_async_context(aioudp.connect(HOST, free_port))
            for _ in range(peers)
        ]
        for conn in clients:
            await conn.send(b"hello")
            assert await conn.recv() == b"hello"
            assert conn.remote_address == (HOST, free_port)

        assert all(local == (HOST, free_port) for local, _ in seen)
        assert Counter(remote for _, remote in seen) == Counter(
            conn.local_address for conn in clients
        )


@given(good=st.lists(st.booleans(), min_size=1, max_size=6).filter(any))
@pytest.mark.asyncio
@bounded
async def test_raising_handler_does_not_affect_other_peers(
    free_port: int, good: list[bool]
) -> None:
    async def fragile(conn: aioudp.Connection) -> None:
        if await conn.recv() == b"boom":
            raise RuntimeError
        await echo(conn)

    async with aioudp.serve(HOST, free_port, fragile), AsyncExitStack() as stack:
        clients = [
            await stack.enter_async_context(aioudp.connect(HOST, free_port))
            for _ in good
        ]
        for conn, is_good in zip(clients, good):
            await conn.send(b"hi" if is_good else b"boom")
        for conn, is_good in zip(clients, good):
            if is_good:
                await conn.send(b"still there?")
                assert await conn.recv() == b"still there?"


@given(vanished=st.integers(1, 4))
@pytest.mark.asyncio
@bounded
async def test_server_keeps_serving_after_peers_vanish(
    free_port: int, vanished: int
) -> None:
    reply = asyncio.Event()
    replied = asyncio.Semaphore(0)

    async def delayed_echo(conn: aioudp.Connection) -> None:
        async for data in conn:
            await reply.wait()
            await conn.send(data)
            replied.release()

    async with aioudp.serve(HOST, free_port, delayed_echo):
        for _ in range(vanished):
            async with aioudp.connect(HOST, free_port) as gone:
                await gone.send(b"reply to a closed port")
        reply.set()
        for _ in range(vanished):
            await replied.acquire()
        await asyncio.sleep(SETTLE)
        async with aioudp.connect(HOST, free_port) as conn:
            await conn.send(b"still serving?")
            assert await conn.recv() == b"still serving?"


@given(queue_size=st.integers(1, 4), overflow=st.integers(1, 32))
@pytest.mark.asyncio
@bounded
async def test_full_client_queue_drops_silently(
    free_port: int, queue_size: int, overflow: int
) -> None:
    errors = record_loop_errors(asyncio.get_running_loop())
    count = queue_size + overflow
    all_echoed = asyncio.Event()

    async def echo_then_signal(conn: aioudp.Connection) -> None:
        for _ in range(count):
            await conn.send(await conn.recv())
        all_echoed.set()

    async with aioudp.serve(HOST, free_port, echo_then_signal):
        async with aioudp.connect(HOST, free_port, queue_size=queue_size) as conn:
            for i in range(count):
                await conn.send(i.to_bytes(2, "big"))
            await all_echoed.wait()
            await asyncio.sleep(SETTLE)
        with pytest.raises(ConnectionClosedError):
            await conn.recv()
    assert errors == []


@given(queue_size=st.integers(1, 4), overflow=st.integers(1, 32))
@pytest.mark.asyncio
@bounded
async def test_full_server_queue_drops_silently(
    free_port: int, queue_size: int, overflow: int
) -> None:
    errors = record_loop_errors(asyncio.get_running_loop())
    handler_started = asyncio.Event()

    async def stall(_conn: aioudp.Connection) -> None:
        handler_started.set()
        await asyncio.Event().wait()

    async with aioudp.serve(HOST, free_port, stall, queue_size=queue_size):
        async with aioudp.connect(HOST, free_port) as conn:
            for i in range(queue_size + overflow):
                await conn.send(i.to_bytes(2, "big"))
            await handler_started.wait()
            await asyncio.sleep(SETTLE)
    await asyncio.sleep(SETTLE)
    assert errors == []


@given(peers=st.integers(1, 6))
@pytest.mark.asyncio
@bounded
async def test_serve_exit_finishes_handlers(free_port: int, peers: int) -> None:
    finished: list[aioudp.Connection] = []

    async def echo_once_then_block(conn: aioudp.Connection) -> None:
        try:
            await conn.send(await conn.recv())
            await asyncio.Event().wait()
        finally:
            finished.append(conn)

    async with aioudp.serve(HOST, free_port, echo_once_then_block):
        for _ in range(peers):
            async with aioudp.connect(HOST, free_port) as conn:
                await conn.send(b"ping")
                assert await conn.recv() == b"ping"
    assert len(finished) == peers


@pytest.mark.asyncio
@bounded
async def test_unreachable_server_does_not_raise_into_loop(free_port: int) -> None:
    errors = record_loop_errors(asyncio.get_running_loop())
    async with aioudp.connect(HOST, free_port) as conn:
        for _ in range(3):
            await conn.send(b"anyone?")
            await asyncio.sleep(SETTLE)
    assert errors == []


payloads = st.binary(min_size=1, max_size=MAX_STATEFUL_PAYLOAD)


class ClientLifecycle(RuleBasedStateMachine):
    def __init__(self, port: int) -> None:
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self.loop_errors = record_loop_errors(self.loop)
        self.port = port
        self.server = AsyncExitStack()
        self.run(self.server.enter_async_context(aioudp.serve(HOST, port, echo)))
        self.connect()

    def run(self, awaitable: Awaitable[T], timeout: float = TIMEOUT) -> T:
        return self.loop.run_until_complete(asyncio.wait_for(awaitable, timeout))

    def connect(self) -> None:
        self.client = AsyncExitStack()
        self.conn = self.run(
            self.client.enter_async_context(aioudp.connect(HOST, self.port))
        )
        self.closed = False
        self.in_flight: Counter[bytes] = Counter()

    def is_open(self) -> bool:
        return not self.closed

    def is_closed(self) -> bool:
        return self.closed

    @precondition(
        lambda self: self.is_open() and sum(self.in_flight.values()) < MAX_IN_FLIGHT
    )
    @rule(data=payloads)
    def send(self, data: bytes) -> None:
        self.run(self.conn.send(data))
        self.in_flight[data] += 1

    @precondition(lambda self: self.is_open() and self.in_flight)
    @rule()
    def recv(self) -> None:
        data = self.run(self.conn.recv())
        assert data in self.in_flight, "received bytes that were never sent"
        self.in_flight -= Counter([data])

    @precondition(is_open)
    @rule()
    def send_empty(self) -> None:
        with pytest.raises(ValueError):
            self.run(self.conn.send(b""))

    @precondition(is_open)
    @rule()
    def close(self) -> None:
        self.run(self.client.aclose())
        self.closed = True

    @precondition(is_closed)
    @rule(data=payloads)
    def send_after_close(self, data: bytes) -> None:
        with pytest.raises(ConnectionClosedError):
            self.run(self.conn.send(data))

    @precondition(is_closed)
    @rule()
    def recv_after_close(self) -> None:
        with pytest.raises(ConnectionClosedError):
            self.run(self.conn.recv(), IMMEDIATE)

    @precondition(is_closed)
    @rule()
    def reconnect(self) -> None:
        self.connect()

    @invariant()
    def nothing_raised_into_loop(self) -> None:
        assert self.loop_errors == []

    def teardown(self) -> None:
        try:
            if self.is_open():
                self.run(self.client.aclose())
            self.run(self.server.aclose())
        finally:
            self.loop.close()
        assert self.loop_errors == []


def test_client_lifecycle(free_port: int) -> None:
    run_state_machine_as_test(lambda: ClientLifecycle(free_port))
