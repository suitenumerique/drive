"""
Services for WOPI access
https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/concepts#access-token
"""

from dataclasses import dataclass
from datetime import timedelta
from secrets import token_urlsafe
from uuid import UUID

from django.conf import settings
from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.core.cache import cache
from django.utils import timezone

from core.models import Item, User


class AccessError(Exception):
    """Base exception for access errors."""


class AccessUserItemNotFoundError(AccessError):
    """Exception for when a user or item is not found."""


class AccessUserItemInvalidDataError(AccessError):
    """Exception for when a user or item has invalid data."""


class AccessUserItemNotAllowed(AccessError):
    """Exception for when a user is not allowed to access an item."""


@dataclass
class AccessUserItem:
    """Service for accessing a user item"""

    item: Item
    user: AbstractUser

    def to_dict(self):
        """Convert the access user item to a dictionary"""
        return {
            "item": str(self.item.id),
            "user": str(self.user.id) if not self.user.is_anonymous else None,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Convert a dictionary to an access user item"""
        try:
            return cls(
                item=Item.objects.get(id=UUID(data["item"])),
                user=User.objects.get(id=UUID(data["user"]))
                if data["user"]
                else AnonymousUser(),
            )
        except (Item.DoesNotExist, User.DoesNotExist) as error:
            raise AccessUserItemNotFoundError("Resource not found") from error
        except (KeyError, ValueError) as error:
            raise AccessUserItemInvalidDataError("Invalid data") from error


class AccessUserItemService:
    """Service managing the access token for WOPI."""

    @staticmethod
    def generate_token():
        """Generate a random access token"""
        return token_urlsafe()

    def insert_new_access(self, item: Item, user: AbstractUser) -> tuple[str, int]:
        """
        Insert a new access token for the user and item. Return an access_token and access_token_ttl
        access_token_ttl must be a timestamp in milliseconds
        """
        abilities = item.get_abilities(user)
        if not abilities["retrieve"]:
            raise AccessUserItemNotAllowed()
        token = self.generate_token()
        access_user_item = AccessUserItem(item=item, user=user)
        token_eol = timezone.now() + timedelta(
            seconds=settings.WOPI_ACCESS_TOKEN_TIMEOUT
        )
        cache.set(
            token,
            access_user_item.to_dict(),
            timeout=settings.WOPI_ACCESS_TOKEN_TIMEOUT,
        )
        return token, int(round(token_eol.timestamp())) * 1000

    def get_access_user_item(self, token: str) -> AccessUserItem:
        """Get the access user item for the token"""
        data = cache.get(token)
        if data is None:
            raise AccessUserItemNotFoundError("Resource not found")
        return AccessUserItem.from_dict(data)
