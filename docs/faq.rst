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
