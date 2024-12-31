# AioUDP

[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![codecov](https://codecov.io/gh/ThatXliner/aioudp/branch/main/graph/badge.svg)](https://codecov.io/gh/ThatXliner/aioudp)

[![Documentation Status](https://readthedocs.org/projects/aioudp/badge/?version=latest)](https://aioudp.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/ThatXliner/aioudp/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ThatXliner/aioudp/actions/workflows/ci.yml)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/aioudp)](https://pypi.org/project/aioudp)
[![PyPI](https://img.shields.io/pypi/v/aioudp)](https://pypi.org/project/aioudp)
[![PyPI - License](https://img.shields.io/pypi/l/aioudp)](#license)

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

    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    # Optional. This is for properly exiting the server when Ctrl-C is pressed
    # or when the process is killed/terminated
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

## Installation

You can get this project via `pip`

```bash
$ pip install aioudp
```


Or, if you're using [Poetry](https://python-poetry.org)

```bash
$ poetry add aioudp
```

> [!NOTE]
> This library provides no other abstractions over the existing UDP interface in `asyncio` other than the `async`/`await`-based API. This means there is no implicit protocol handled in this library such as [QUIC](https://en.wikipedia.org/wiki/QUIC). You must write your own, or find another library.

## See also

- [AnyIO](https://anyio.readthedocs.io/en/stable/index.html), a broader asynchronous networking and concurrency library for abstracting over any `async` IO implementation. It has a [similar API](https://anyio.readthedocs.io/en/stable/networking.html#working-with-udp-sockets) (which I didn't know about before I wrote this library)
- [WebSockets](https://websockets.readthedocs.io/en/stable/), a library for Python to interact with WebSockets. Its API heavily inspired the design of AioUDP.
- [QUIC](https://en.wikipedia.org/wiki/QUIC), a faster protocol similar to TCP, built on UDP.
- [AioQUIC](https://github.com/aiortc/aioquic), a Python implementation of QUIC.

## License

Copyright © 2021, Bryan Hu

This project is licensed under the [GNU GPL v3+](https://github.com/ThatXliner/aioudp/blob/main/LICENSE.txt).

In short, this means you can do anything with it (distribute, modify, sell) but if you were to publish your changes, you must make the source code and build instructions readily available.

If you are a company using this project and want an exception, email me at [thatxliner@gmail.com](mailto:thatxliner@gmail.com) and we can discuss.
