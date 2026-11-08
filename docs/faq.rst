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

Otherwise, if you know what you're doing, just `.encode <https://docs.python.org/3/library/stdtypes.html#str.encode>`_ your strings.

.. _faq-it-hangs:

Why is my code hanging?
-----------------------

You may be calling ``recv`` when the other side never sent anything, or the server's handler raised an exception.
The server reports handler exceptions through the event loop's exception handler, which logs them by default.
To stop waiting, :ref:`add a timeout <faq-add-timeout>`.
If your client calls ``recv`` before it sends anything, see :ref:`faq-server-first`.

.. _faq-server-first:

Can the server send the first message?
--------------------------------------

No. UDP has no handshake, so the server learns about a client only when the client's first message arrives.
That message starts the handler.
A client that calls ``recv`` before it sends anything waits forever.

Send first from the client, even if the message only says hello:

.. code-block:: python

    async with aioudp.connect("localhost", 9999) as connection:
        await connection.send(b"hello")
        greeting = await connection.recv()

Versions before 2.0 hid this problem.
The client sent ``b"trash"`` when it connected, and the server dropped the first message from every client.
Version 2.0 removed that workaround.
Servers that did not use aioudp received the bogus message,
and when no server was listening, the extra message caused ICMP errors such as ``ConnectionResetError``
(`#18 <https://github.com/ThatXliner/aioudp/issues/18>`_).

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
        print("timeout!")

Where ``func`` is the function you want to add a timeout to.
