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

You may be using ``recv`` when the server didn't send anything to the client or an exception happened in the server. If this is the case, you should :ref:`add a timeout <faq-add-timeout>`.


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
