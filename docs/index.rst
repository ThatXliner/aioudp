Welcome to AioUDP's documentation!
==================================

.. toctree::
    :titlesonly:
    :maxdepth: 2
    :caption: Contents:

    quickstart
    faq
    api_ref

AioUDP is a library that provides a simple interface to asynchronous UDP communication.

Here's an example of a simple UDP echo server serving at ``localhost`` at port ``9999``:

.. code-block:: python

    import aioudp
    import asyncio

    async def main():
        async def handler(connection):
            async for message in connection:
                await connection.send(message)
        async with aioudp.serve("localhost", 9999, handler):
            await asyncio.Future()  # Serve forever

    if __name__ == '__main__':
        asyncio.run(main())

And the client that will send ``b"Hello world!"`` to the server:

.. code-block:: python

    import aioudp
    import asyncio

    async def main():
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.send(b"Hello world!")
            assert await connection.recv() == b"Hello world!"

    if __name__ == '__main__':
        asyncio.run(main())

.. seealso::
    :ref:`faq-why-bytes`

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
