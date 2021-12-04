# AioUDP

[![Documentation Status](https://readthedocs.org/projects/aioudp/badge/?version=latest)](https://aioudp.readthedocs.io/en/latest/?badge=latest)

> A better API for asynchronous UDP

A [websockets](https://websockets.readthedocs.io/en/stable/index.html)-like API for [UDP](https://en.wikipedia.org/wiki/User_Datagram_Protocol)

Here's an example echo server:

```py
import aioudp
import asyncio
import signal

async def main():
    async def handler(connection):
        async for message in connection:
            await connection.send(message)

    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    async with aioudp.serve("localhost", 9999, handler):
        await stop  # Serve forever

if __name__ == '__main__':
    asyncio.run(main())
```

And a client to connect to the server:

```py
import aioudp
import asyncio

async def main():
    async with aioudp.connect("localhost", 9999) as connection:
        await connection.send(b"Hello world!")
        assert await connection.recv() == b"Hello world!"

if __name__ == '__main__':
    asyncio.run(main())
```
