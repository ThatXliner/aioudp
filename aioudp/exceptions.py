"""Exceptions this library might raise"""


class AioUDPError(Exception):
    """Base exception for this library

    All exceptions this library will raise will subclass this
    """


class ConnectionClosedError(AioUDPError):
    """When a connection is closed and you tried to send/recieve a message"""
