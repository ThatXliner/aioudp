Quickstart
==========

Installation
------------

Install this library via pip:

.. code-block::

    $ pip install aioudp

Example Usage
-------------

Here's a simple PA system with `PyAudio <https://people.csail.mit.edu/hubert/pyaudio/>`_:


.. code-block:: python
    :caption: Server code (speaker)

    import asyncio
    import signal

    import pyaudio

    import aioudp

    # Doesn't have to be "\x00" and "\x01". Any unique value would do
    ACCEPT = b"\x00"
    DECLINE = b"\x01"
    TERMINATOR = b"DONE"  # Could be anything that will never be audio data
    connections = set()


    async def main():
        # Configuration for PyAudio
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100

        async def handler(connection: aioudp.Connection) -> None:
            # Make sure only one person uses the PA at a time
            if connections:
                await connection.send(DECLINE)
                return
            await connection.send(ACCEPT)
            connections.add(None)

            # PyAudio initialization black magic
            p = pyaudio.PyAudio()
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                output=True,
                frames_per_buffer=CHUNK,
                rate=RATE,
            )

            async for data in connection:
                # Until b"DONE" is recieved, play the data
                if data == TERMINATOR:
                    break
                stream.write(data)

            # Uninitalize PyAudio stuff
            stream.stop_stream()
            stream.close()
            p.terminate()

            connections.remove(None)

        loop = asyncio.get_running_loop()
        stop = loop.create_future()
        # This way, we can CTRl-C it properly
        loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

        # "0.0.0.0" to expose globally. Serve at port 9999
        async with aioudp.serve("0.0.0.0", 9999, handler):
            await stop


    if __name__ == "__main__":
        asyncio.run(main())

.. code-block:: python
    :caption: User code (microphone)

    import asyncio

    import pyaudio

    import aioudp

    DECLINE = b"\x01"
    TERMINATOR = b"DONE"


    async def main() -> None:
        # Configuration for PyAudio
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100

        # Let's connect to my Raspberry Pi on the local network
        async with aioudp.connect("raspberrypi", 9999) as connection:
            if await connection.recv() == DECLINE:
                print("Someone else is already using the PA system :(")
                return

            # Again, some PyAudio black magic.
            # This time set up for input
            p = pyaudio.PyAudio()
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                input=True,
                rate=RATE,
                frames_per_buffer=CHUNK,
            )
            # Continue recording and stream recording
            # Until CTRL-C
            try:
                while True:
                    await connection.send(stream.read(CHUNK))
            except KeyboardInterrupt:
                await connection.send(TERMINATOR)

            # De-init PyAudio
            stream.stop_stream()
            stream.close()
            p.terminate()


    if __name__ == "__main__":
        asyncio.run(main())
