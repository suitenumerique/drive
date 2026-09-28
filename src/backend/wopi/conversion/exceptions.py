"""Exceptions for server-to-server file conversion."""


class ConversionError(Exception):
    """Base exception for conversion service failures."""


class ConversionPermissionDenied(ConversionError):
    """Raised when the user cannot convert the source item."""


class ConversionRejected(ConversionError):
    """Raised when the conversion request cannot be satisfied."""


class ConversionMisconfigured(ConversionError):
    """Raised when the active conversion backend is missing required settings."""


class ConversionProviderError(ConversionError):
    """Raised when the document server fails to deliver the converted file."""
