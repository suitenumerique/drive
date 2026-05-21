"""Wopi enums module"""

from enum import StrEnum


class WopiActions(StrEnum):
    """Wopi actions enum"""

    EDIT = "edit"
    VIEW = "view"
    CONVERT = "convert"
