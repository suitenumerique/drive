"""Exceptions for the authentication module."""


class EmailNotAlphaAuthorized(Exception):
    """Exception raised when an email is not whitelisted."""


class UserCannotAccessApp(Exception):
    """Exception raised when a user cannot access the app."""
