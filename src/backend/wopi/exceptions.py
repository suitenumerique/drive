"""WOPI exceptions module."""


class WopiRequestSignatureError(Exception):
    """Exception for when a request signature is invalid."""

    def __init__(self, message="Invalid request signature"):
        self.message = message
        super().__init__(self.message)
