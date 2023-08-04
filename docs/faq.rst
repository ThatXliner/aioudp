Frequently Asked Questions
==========================

Common questions you may have

.. _faq-why-bytes:

Why do the messages need to be in bytes?
----------------------------------------

Because it makes sense. UDP is unreliable but fast, making it a good choice for streaming audio/video.

If you're trying to send strings, you're probably misusing this library.
I recommend a good TCP (to be precise, `WebSockets <https://en.wikipedia.org/wiki/WebSocket>`_)
`library called websockets <https://websockets.readthedocs.io/en/stable/>`_.
It has a similar API to this library. In fact, this library's API was inspired by the websockets library.

.. _faq-it-hangs:

Why is my code hanging?
-----------------------

If your code is trying to ``.recv()`` something on the client side but
that is hanging, the following may be the case:

 - The server didn't send anything to the client
 - An exception happened in the server.

Because these scenarios can happen, you should :ref:`add a timeout <faq-add-timeout>`.

.. _faq-hang:

Otherwise, there's a chance that you've been trying to immediately ``.recv()`` upon
connecting on the client-side. For example this code hangs:

.. code-block:: python
    :caption: Client code
    :emphasize-lines: 7

    import asyncio
    import aioudp


    async def main():
        async with aioudp.connect("localhost", 9999) as connection:
            assert await connection.recv() == b"Hello world!"

    if __name__ == '__main__':
        asyncio.run(main())

.. code-block:: python
    :caption: Server code

    import asyncio
    import aioudp


    async def main():
        async def handler(connection):
            await connection.send(b"Hello world!")
        async with aioudp.serve("localhost", 9999, handler):
            await asyncio.Future()

    if __name__ == '__main__':
        asyncio.run(main())

Because the client code is trying to receive the message immediately upon connection.
This bug (issue `#2 <https://github.com/ThatXliner/aioudp/issues/2>`_) used to not exist (patched in PR `#3 <https://github.com/ThatXliner/aioudp/pull/3>`_)
but as of version ``1.0``, I've decided that this violates the promise of being protocol-agnostic.

If you really need to do so, a workaround is implementing an initial "trash" message like so:

.. code-block:: python
    :caption: Client code
    :emphasize-lines: 7

    import asyncio
    import aioudp


    async def main():
        async with aioudp.connect("localhost", 9999) as connection:
            await connection.send(b"TRASH")
            assert await connection.recv() == b"Hello world!"

    if __name__ == '__main__':
        asyncio.run(main())

.. code-block:: python
    :caption: Server code
    :emphasize-lines: 7

    import asyncio
    import aioudp


    async def main():
        async def handler(connection):
            await connection.recv()
            await connection.send(b"Hello world!")
        async with aioudp.serve("localhost", 9999, handler):
            await asyncio.Future()

    if __name__ == '__main__':
        asyncio.run(main())

.. note::

    This "workaround" used to be the "patch" that I made to fix this issue


.. _faq-add-timeout:

How can I add a timeout?
------------------------

This is not specific to AioUDP, but rather a general asyncio-related question.

You should use `asyncio.wait_for <https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for>`_

Example:

.. code-block:: python

    try:
        await asyncio.wait_for(func(), timeout=0.01)
    except asyncio.TimeoutError:
        print('timeout!')

Where ``func`` is the function you want to add a timeout to.

.. _faq-comparison:

How does this compare to other libraries?
-----------------------------------------

.. todo::

    Benchmark speed

+---------+-------------------------+--------------------+----------------------------+
| Library | Example echo server LOC | Example client LOC | Framework                  |
+=========+=========================+====================+============================+
| AioUDP  | 15                      | 11                 | Asyncio                    |
+---------+-------------------------+--------------------+----------------------------+
| Asyncio | 34                      | 47                 | Asyncio                    |
+---------+-------------------------+--------------------+----------------------------+
| AnyIO   | 12                      | 12                 | Any asynchronous framework |
+---------+-------------------------+--------------------+----------------------------+

Asyncio
~~~~~~~

Pros: Built-in
Cons: Hard to use

Python has built-in UDP functionality but it's so painful to use: the example echo server is 2 times longer than AioUDP's example echo server.

AnyIO
~~~~~~~

Pros: Simple interface
Cons: None

AnyIO is a good alternative to AioUDP. I actually wrote this library thinking no one has made an asynchronous API for UDP yet, but apparently AnyIO already did, and async-framework-agnostic!
