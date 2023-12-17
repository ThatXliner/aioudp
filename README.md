# AioUDP

[![Documentation Status](https://readthedocs.org/projects/aioudp/badge/?version=latest)](https://aioudp.readthedocs.io/en/latest/?badge=latest) [![codecov](https://codecov.io/gh/ThatXliner/aioudp/branch/main/graph/badge.svg?token=xZ7HVG8Owm)](https://codecov.io/gh/ThatXliner/aioudp) [![CI](https://github.com/ThatXliner/aioudp/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ThatXliner/aioudp/actions/workflows/ci.yml)

> A better API for asynchronous UDP

A [websockets](https://websockets.readthedocs.io/en/stable/index.html)-like API for [UDP](https://en.wikipedia.org/wiki/User_Datagram_Protocol)

Here's an example echo server:

```py
import asyncio
import signal

import aioudp


async def main():
    async def handler(connection):
        async for message in connection:
            await connection.send(message)

    # Optional. This is for properly exiting the server when Ctrl-C is pressed
    # or when the process is killed/terminated
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

    # Serve the server
    async with aioudp.serve("localhost", 9999, handler):
        await stop  # Serve forever

if __name__ == '__main__':
    asyncio.run(main())
```

And a client to connect to the server:

```py
import asyncio

import aioudp


async def main():
    async with aioudp.connect("localhost", 9999) as connection:
        await connection.send(b"Hello world!")
        assert await connection.recv() == b"Hello world!"

if __name__ == '__main__':
    asyncio.run(main())
```

NOTE: This library provides no other abstractions over the existing UDP interface in `asyncio` other than the `async`/`await`-based API. This means there is no implicit protocol handled in this library such a [QUIC](https://en.wikipedia.org/wiki/QUIC). You must write your own, or find another library.

## See also

- [AnyIO](https://anyio.readthedocs.io/en/stable/index.html), a broader asynchronous networking and concurrency library for abstracting over any `async` IO implementation. It has a [similar API](https://anyio.readthedocs.io/en/stable/networking.html#working-with-udp-sockets) (which I didn't know about before I wrote this library)
- [WebSockets](https://websockets.readthedocs.io/en/stable/), a library for Python to interact with WebSockets. Its API heavily inspired the design of AioUDP.
- [QUIC](https://en.wikipedia.org/wiki/QUIC), a faster protocol similar to TCP, built on UDP.
- [AioQUIC](https://github.com/aiortc/aioquic), the Python implementation of QUIC.
