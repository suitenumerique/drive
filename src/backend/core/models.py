"""
Declare and configure the models for the drive core application
"""
# pylint: disable=too-many-lines

import smtplib
import uuid
from datetime import timedelta
from logging import getLogger

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.sites.models import Site
from django.core import mail, validators
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import models, transaction
from django.db.models.functions import Left, Length
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.functional import cached_property, lazy
from django.utils.translation import get_language, override
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError
from timezone_field import TimeZoneField
from treebeard.mp_tree import MP_Node

logger = getLogger(__name__)


def get_trashbin_cutoff():
    """
    Calculate the cutoff datetime for soft-deleted items based on the retention policy.

    The function returns the current datetime minus the number of days specified in
    the TRASHBIN_CUTOFF_DAYS setting, indicating the oldest date for items that can
    remain in the trash bin.

    Returns:
        datetime: The cutoff datetime for soft-deleted items.
    """
    return timezone.now() - timedelta(days=settings.TRASHBIN_CUTOFF_DAYS)


class LinkRoleChoices(models.TextChoices):
    """Defines the possible roles a link can offer on a item."""

    READER = "reader", _("Reader")  # Can read
    EDITOR = "editor", _("Editor")  # Can read and edit


class RoleChoices(models.TextChoices):
    """Defines the possible roles a user can have in a resource."""

    READER = "reader", _("Reader")  # Can read
    EDITOR = "editor", _("Editor")  # Can read and edit
    ADMIN = "administrator", _("Administrator")  # Can read, edit, delete and share
    OWNER = "owner", _("Owner")


PRIVILEGED_ROLES = [RoleChoices.ADMIN, RoleChoices.OWNER]


class LinkReachChoices(models.TextChoices):
    """Defines types of access for links"""

    RESTRICTED = (
        "restricted",
        _("Restricted"),
    )  # Only users with a specific access can read/edit the item
    AUTHENTICATED = (
        "authenticated",
        _("Authenticated"),
    )  # Any authenticated user can access the item
    PUBLIC = "public", _("Public")  # Even anonymous users can access the item


class ItemTypeChoices(models.TextChoices):
    """Defines the types of items that can be created."""

    FOLDER = "folder", _("Folder")
    LINK = "link", _("Link")
    FILE = "file", _("File")


class ItemUploadStateChoices(models.TextChoices):
    """Defines the possible states of an item."""

    PENDING = "pending", _("Pending")
    UPLOADED = "uploaded", _("Uploaded")


class DuplicateEmailError(Exception):
    """Raised when an email is already associated with a pre-existing user."""

    def __init__(self, message=None, email=None):
        """Set message and email to describe the exception."""
        self.message = message
        self.email = email
        super().__init__(self.message)


class BaseModel(models.Model):
    """
    Serves as an abstract base model for other models, ensuring that records are validated
    before saving as Django doesn't do it by default.

    Includes fields common to all models: a UUID primary key and creation/update timestamps.
    """

    id = models.UUIDField(
        verbose_name=_("id"),
        help_text=_("primary key for the record as UUID"),
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    created_at = models.DateTimeField(
        verbose_name=_("created on"),
        help_text=_("date and time at which a record was created"),
        auto_now_add=True,
        editable=False,
    )
    updated_at = models.DateTimeField(
        verbose_name=_("updated on"),
        help_text=_("date and time at which a record was last updated"),
        auto_now=True,
        editable=False,
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Call `full_clean` before saving."""
        self.full_clean()
        super().save(*args, **kwargs)


class UserManager(auth_models.UserManager):
    """Custom manager for User model with additional methods."""

    def get_user_by_sub_or_email(self, sub, email):
        """Fetch existing user by sub or email."""
        try:
            return self.get(sub=sub)
        except self.model.DoesNotExist as err:
            if not email:
                return None

            if settings.OIDC_FALLBACK_TO_EMAIL_FOR_IDENTIFICATION:
                try:
                    return self.get(email=email)
                except self.model.DoesNotExist:
                    pass
            elif (
                self.filter(email=email).exists()
                and not settings.OIDC_ALLOW_DUPLICATE_EMAILS
            ):
                raise DuplicateEmailError(
                    _(
                        "We couldn't find a user with this sub but the email is already "
                        "associated with a registered user."
                    )
                ) from err
        return None


class User(AbstractBaseUser, BaseModel, auth_models.PermissionsMixin):
    """User model to work with OIDC only authentication."""

    sub_validator = validators.RegexValidator(
        regex=r"^[\w.@+-:]+\Z",
        message=_(
            "Enter a valid sub. This value may contain only letters, "
            "numbers, and @/./+/-/_/: characters."
        ),
    )

    sub = models.CharField(
        _("sub"),
        help_text=_(
            "Required. 255 characters or fewer. Letters, numbers, and @/./+/-/_/: characters only."
        ),
        max_length=255,
        unique=True,
        validators=[sub_validator],
        blank=True,
        null=True,
    )

    full_name = models.CharField(_("full name"), max_length=100, null=True, blank=True)
    short_name = models.CharField(_("short name"), max_length=20, null=True, blank=True)

    email = models.EmailField(_("identity email address"), blank=True, null=True)

    # Unlike the "email" field which stores the email coming from the OIDC token, this field
    # stores the email used by staff users to login to the admin site
    admin_email = models.EmailField(
        _("admin email address"), unique=True, blank=True, null=True
    )

    language = models.CharField(
        max_length=10,
        choices=lazy(lambda: settings.LANGUAGES, tuple)(),
        default=settings.LANGUAGE_CODE,
        verbose_name=_("language"),
        help_text=_("The language in which the user wants to see the interface."),
    )
    timezone = TimeZoneField(
        choices_display="WITH_GMT_OFFSET",
        use_pytz=False,
        default=settings.TIME_ZONE,
        help_text=_("The timezone in which the user wants to see times."),
    )
    is_device = models.BooleanField(
        _("device"),
        default=False,
        help_text=_("Whether the user is a device or a real user."),
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )

    objects = UserManager()

    USERNAME_FIELD = "admin_email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "drive_user"
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.email or self.admin_email or str(self.id)

    def save(self, *args, **kwargs):
        """
        If it's a new user, give its user access to the items to which s.he was invited.
        """
        is_adding = self._state.adding
        super().save(*args, **kwargs)

        if is_adding:
            self._convert_valid_invitations()

    def _convert_valid_invitations(self):
        """
        Convert valid invitations to item accesses.
        Expired invitations are ignored.
        """
        valid_invitations = Invitation.objects.filter(
            email=self.email,
            created_at__gte=(
                timezone.now()
                - timedelta(seconds=settings.INVITATION_VALIDITY_DURATION)
            ),
        ).select_related("item")

        if not valid_invitations.exists():
            return

        ItemAccess.objects.bulk_create(
            [
                ItemAccess(user=self, item=invitation.item, role=invitation.role)
                for invitation in valid_invitations
            ]
        )

        # Set creator of items if not yet set (e.g. items created via server-to-server API)
        item_ids = [invitation.item_id for invitation in valid_invitations]
        Item.objects.filter(id__in=item_ids, creator__isnull=True).update(creator=self)

        valid_invitations.delete()

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Email this user."""
        if not self.email:
            raise ValueError("User has no email address.")
        mail.send_mail(subject, message, from_email, [self.email], **kwargs)

    @cached_property
    def teams(self):
        """
        Get list of teams in which the user is, as a list of strings.
        Must be cached if retrieved remotely.
        """
        return []


class BaseAccess(BaseModel):
    """Base model for accesses to handle resources."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    team = models.CharField(max_length=100, blank=True)
    role = models.CharField(
        max_length=20, choices=RoleChoices.choices, default=RoleChoices.READER
    )

    class Meta:
        abstract = True

    def _get_abilities(self, resource, user):
        """
        Compute and return abilities for a given user taking into account
        the current state of the object.
        """
        roles = []
        if user.is_authenticated:
            teams = user.teams
            try:
                roles = self.user_roles or []
            except AttributeError:
                try:
                    roles = resource.accesses.filter(
                        models.Q(user=user) | models.Q(team__in=teams),
                    ).values_list("role", flat=True)
                except (self._meta.model.DoesNotExist, IndexError):
                    roles = []

        is_owner_or_admin = bool(
            set(roles).intersection({RoleChoices.OWNER, RoleChoices.ADMIN})
        )
        if self.role == RoleChoices.OWNER:
            can_delete = (
                RoleChoices.OWNER in roles
                and resource.accesses.filter(role=RoleChoices.OWNER).count() > 1
            )
            set_role_to = (
                [RoleChoices.ADMIN, RoleChoices.EDITOR, RoleChoices.READER]
                if can_delete
                else []
            )
        else:
            can_delete = is_owner_or_admin
            set_role_to = []
            if RoleChoices.OWNER in roles:
                set_role_to.append(RoleChoices.OWNER)
            if is_owner_or_admin:
                set_role_to.extend(
                    [RoleChoices.ADMIN, RoleChoices.EDITOR, RoleChoices.READER]
                )

        # Remove the current role as we don't want to propose it as an option
        try:
            set_role_to.remove(self.role)
        except ValueError:
            pass

        return {
            "destroy": can_delete,
            "update": bool(set_role_to),
            "partial_update": bool(set_role_to),
            "retrieve": bool(roles),
            "set_role_to": set_role_to,
        }


class Item(MP_Node, BaseModel):
    """Item in the tree."""

    title = models.CharField(_("title"), max_length=255)
    link_reach = models.CharField(
        max_length=20,
        choices=LinkReachChoices.choices,
        default=LinkReachChoices.RESTRICTED,
    )
    link_role = models.CharField(
        max_length=20, choices=LinkRoleChoices.choices, default=LinkRoleChoices.READER
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="items_created",
        blank=True,
        null=True,
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    ancestors_deleted_at = models.DateTimeField(null=True, blank=True)

    # Tree structure
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    steplen = 7  # nb siblings max: 3,521,614,606,208
    node_order_by = []  # Manual ordering

    path = models.CharField(max_length=7 * 36, unique=True, db_collation="C")

    filename = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(
        max_length=30,
        choices=ItemTypeChoices.choices,
        default=ItemTypeChoices.FOLDER,
    )
    upload_state = models.CharField(
        max_length=20,
        choices=ItemUploadStateChoices.choices,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "drive_item"
        ordering = ("path",)
        verbose_name = _("Item")
        verbose_name_plural = _("Items")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(deleted_at__isnull=True)
                    | models.Q(deleted_at=models.F("ancestors_deleted_at"))
                ),
                name="check_deleted_at_matches_ancestors_deleted_at_when_set",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    models.Q(type=ItemTypeChoices.FILE, filename__isnull=False)
                    | models.Q(
                        ~models.Q(type=ItemTypeChoices.FILE), filename__isnull=True
                    )
                ),
                name="check_filename_set_for_files",
            ),
        ]

    def __str__(self):
        return str(self.title) if self.title else str(_("Untitled Item"))

    def save(self, *args, **kwargs):
        """Set the upload state to pending if it's the first save and it's a file"""
        if self.created_at is None and self.type == ItemTypeChoices.FILE:
            self.upload_state = ItemUploadStateChoices.PENDING

        return super().save(*args, **kwargs)

    @property
    def key_base(self):
        """Key base of the location where the item is stored in object storage."""
        if not self.pk:
            raise RuntimeError(
                "The item instance must be saved before requesting a storage key."
            )

        if self.type != ItemTypeChoices.FILE:
            raise RuntimeError("Only files have a storage key.")

        return f"item/{self.pk!s}"

    @property
    def file_key(self):
        """Key used to store the file in object storage."""
        if self.filename is None:
            raise RuntimeError("The item must have a filename to generate a file key.")

        return f"{self.key_base}/{self.filename}"

    def get_nb_accesses_cache_key(self):
        """Generate a unique cache key for each item."""
        return f"item_{self.id!s}_nb_accesses"

    @property
    def nb_accesses(self):
        """Calculate the number of accesses."""
        cache_key = self.get_nb_accesses_cache_key()
        nb_accesses = cache.get(cache_key)

        if nb_accesses is None:
            nb_accesses = ItemAccess.objects.filter(
                item__path=Left(models.Value(self.path), Length("item__path")),
            ).count()
            cache.set(cache_key, nb_accesses)

        return nb_accesses

    def invalidate_nb_accesses_cache(self):
        """
        Invalidate the cache for number of accesses, including on affected descendants.
        """
        for item in Item.objects.filter(path__startswith=self.path).only("id"):
            cache_key = item.get_nb_accesses_cache_key()
            cache.delete(cache_key)

    def get_roles(self, user):
        """Return the roles a user has on an item."""
        if not user.is_authenticated:
            return []

        try:
            roles = self.user_roles or []
        except AttributeError:
            try:
                roles = ItemAccess.objects.filter(
                    models.Q(user=user) | models.Q(team__in=user.teams),
                    item__path=Left(models.Value(self.path), Length("item__path")),
                ).values_list("role", flat=True)
            except (models.ObjectDoesNotExist, IndexError):
                roles = []
        return roles

    @cached_property
    def links_definitions(self):
        """Get links reach/role definitions for the current item and its ancestors."""
        links_definitions = {self.link_reach: {self.link_role}}

        # Ancestors links definitions are only interesting if the item is not the highest
        # ancestor to which the current user has access. Look for the annotation:
        if self.depth > 1 and not getattr(self, "is_highest_ancestor_for_user", False):
            for ancestor in self.get_ancestors().values("link_reach", "link_role"):
                links_definitions.setdefault(ancestor["link_reach"], set()).add(
                    ancestor["link_role"]
                )

        return links_definitions

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user on the item.
        """
        roles = set(
            self.get_roles(user)
        )  # at this point only roles based on specific access

        # Characteristics that are based only on specific access
        is_owner = RoleChoices.OWNER in roles
        is_deleted = self.ancestors_deleted_at and not is_owner
        is_owner_or_admin = (is_owner or RoleChoices.ADMIN in roles) and not is_deleted

        # Compute access roles before adding link roles because we don't
        # want anonymous users to access versions (we wouldn't know from
        # which date to allow them anyway)
        # Anonymous users should also not see item accesses
        has_access_role = bool(roles) and not is_deleted

        # Add roles provided by the item link, taking into account its ancestors

        # Add roles provided by the item link
        links_definitions = self.links_definitions
        public_roles = links_definitions.get(LinkReachChoices.PUBLIC, set())
        authenticated_roles = (
            links_definitions.get(LinkReachChoices.AUTHENTICATED, set())
            if user.is_authenticated
            else set()
        )

        roles = roles | public_roles | authenticated_roles

        can_get = bool(roles) and not is_deleted
        can_update = (
            is_owner_or_admin or RoleChoices.EDITOR in roles
        ) and not is_deleted

        return {
            "accesses_manage": is_owner_or_admin,
            "accesses_view": has_access_role,
            "children_list": can_get,
            "children_create": can_update and user.is_authenticated,
            "destroy": is_owner,
            "favorite": can_get and user.is_authenticated,
            "link_configuration": is_owner_or_admin,
            "invite_owner": is_owner,
            "move": is_owner_or_admin and not self.ancestors_deleted_at,
            "partial_update": can_update,
            "restore": is_owner,
            "retrieve": can_get,
            "media_auth": can_get,
            "update": can_update,
            "upload_ended": is_owner_or_admin,
        }

    def send_email(self, subject, emails, context=None, language=None):
        """Generate and send email from a template."""
        context = context or {}
        domain = Site.objects.get_current().domain
        language = language or get_language()
        context.update(
            {
                "brandname": settings.EMAIL_BRAND_NAME,
                "item": self,
                "domain": domain,
                "link": f"{domain}/items/{self.id}/",
                "logo_img": settings.EMAIL_LOGO_IMG,
            }
        )

        with override(language):
            msg_html = render_to_string("mail/html/invitation.html", context)
            msg_plain = render_to_string("mail/text/invitation.txt", context)
            subject = str(subject)  # Force translation

            try:
                send_mail(
                    subject.capitalize(),
                    msg_plain,
                    settings.EMAIL_FROM,
                    emails,
                    html_message=msg_html,
                    fail_silently=False,
                )
            except smtplib.SMTPException as exception:
                logger.error("invitation to %s was not sent: %s", emails, exception)

    def send_invitation_email(self, email, role, sender, language=None):
        """Method allowing a user to send an email invitation to another user for a item."""
        language = language or get_language()
        role = RoleChoices(role).label
        sender_name = sender.full_name or sender.email
        sender_name_email = (
            f"{sender.full_name:s} ({sender.email})"
            if sender.full_name
            else sender.email
        )

        with override(language):
            context = {
                "title": _("{name} shared an item with you!").format(name=sender_name),
                "message": _(
                    '{name} invited you with the role "{role}" on the following item:'
                ).format(name=sender_name_email, role=role.lower()),
            }
            subject = _("{name} shared an item with you: {title}").format(
                name=sender_name, title=self.title
            )

        self.send_email(subject, [email], context, language)

    @transaction.atomic
    def soft_delete(self):
        """
        Soft delete the item, marking the deletion on descendants.
        We still keep the .delete() method untouched for programmatic purposes.
        """
        if self.deleted_at or self.ancestors_deleted_at:
            raise RuntimeError("This item is already deleted or has deleted ancestors.")

        # Check if any ancestors are deleted
        if self.get_ancestors().filter(deleted_at__isnull=False).exists():
            raise RuntimeError(
                "Cannot delete this item because one or more ancestors are already deleted."
            )

        self.ancestors_deleted_at = self.deleted_at = timezone.now()
        self.save()

        # Mark all descendants as soft deleted
        self.get_descendants().filter(ancestors_deleted_at__isnull=True).update(
            ancestors_deleted_at=self.ancestors_deleted_at
        )

    @transaction.atomic
    def restore(self):
        """Cancelling a soft delete with checks."""
        # This should not happen
        if self.deleted_at is None:
            raise ValidationError({"deleted_at": [_("This item is not deleted.")]})

        if self.deleted_at < get_trashbin_cutoff():
            raise ValidationError(
                {
                    "deleted_at": [
                        _("This item was permanently deleted and cannot be restored.")
                    ]
                }
            )

        # Restore the current item
        self.deleted_at = None

        # Calculate the minimum `deleted_at` among all ancestors
        ancestors_deleted_at = (
            self.get_ancestors()
            .filter(deleted_at__isnull=False)
            .values_list("deleted_at", flat=True)
        )
        self.ancestors_deleted_at = min(ancestors_deleted_at, default=None)
        self.save()

        # Update descendants excluding those who were deleted prior to the deletion of the
        # current item (the ancestor_deleted_at date for those should already by good)
        # The number of deleted descendants should not be too big so we can handcraft a union
        # clause for them:
        deleted_descendants_paths = (
            self.get_descendants()
            .filter(deleted_at__isnull=False)
            .values_list("path", flat=True)
        )
        exclude_condition = models.Q(
            *(models.Q(path__startswith=path) for path in deleted_descendants_paths)
        )
        self.get_descendants().exclude(exclude_condition).update(
            ancestors_deleted_at=self.ancestors_deleted_at
        )

    def add_child(self, **kwargs):
        """Check if the item can have children before adding one."""
        if self.type != ItemTypeChoices.FOLDER:
            raise ValidationError({"type": _("Only folders can have children.")})

        return super().add_child(**kwargs)

    def move(self, target, pos=None):
        if target.type != ItemTypeChoices.FOLDER:
            raise ValidationError(
                {"target": _("Only folders can be targeted when moving an item")}
            )

        return super().move(target, pos)


class LinkTrace(BaseModel):
    """
    Relation model to trace accesses to am item via a link by a logged-in user.
    This is necessary to show the item in the user's list of items even
    though the user does not have a role on the item.
    """

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="link_traces",
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="link_traces")

    class Meta:
        db_table = "drive_link_trace"
        verbose_name = _("Item/user link trace")
        verbose_name_plural = _("Item/user link traces")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "item"],
                name="unique_link_trace_item_user",
                violation_error_message=_(
                    "A link trace already exists for this item/user."
                ),
            ),
        ]

    def __str__(self):
        return f"{self.user!s} trace on item {self.item!s}"


class ItemFavorite(BaseModel):
    """Relation model to store a user's favorite items."""

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="favorited_by_users",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="favorite_items"
    )

    class Meta:
        db_table = "drive_item_favorite"
        verbose_name = _("Item favorite")
        verbose_name_plural = _("Item favorites")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "item"],
                name="unique_item_favorite_user",
                violation_error_message=_(
                    "This item is already targeted by a favorite relation instance "
                    "for the same user."
                ),
            ),
        ]

    def __str__(self):
        return f"{self.user!s} favorite on item {self.item!s}"


class ItemAccess(BaseAccess):
    """Relation model to give access to an item for a user or a team with a role."""

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="accesses",
    )

    class Meta:
        db_table = "drive_item_access"
        ordering = ("-created_at",)
        verbose_name = _("Item/user relation")
        verbose_name_plural = _("Item/user relations")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "item"],
                condition=models.Q(user__isnull=False),  # Exclude null users
                name="unique_item_user",
                violation_error_message=_("This user is already in this item."),
            ),
            models.UniqueConstraint(
                fields=["team", "item"],
                condition=models.Q(team__gt=""),  # Exclude empty string teams
                name="unique_item_team",
                violation_error_message=_("This team is already in this item."),
            ),
            models.CheckConstraint(
                condition=models.Q(user__isnull=False, team="")
                | models.Q(user__isnull=True, team__gt=""),
                name="check_item_access_either_user_or_team",
                violation_error_message=_("Either user or team must be set, not both."),
            ),
        ]

    def __str__(self):
        return f"{self.user!s} is {self.role:s} in item {self.item!s}"

    def save(self, *args, **kwargs):
        """Override save to clear the item's cache for number of accesses."""
        super().save(*args, **kwargs)
        self.item.invalidate_nb_accesses_cache()

    def delete(self, *args, **kwargs):
        """Override delete to clear the item's cache for number of accesses."""
        super().delete(*args, **kwargs)
        self.item.invalidate_nb_accesses_cache()

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user on the item access.
        """
        return self._get_abilities(self.item, user)


class Invitation(BaseModel):
    """User invitation to am item."""

    email = models.EmailField(_("email address"), null=False, blank=False)
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    role = models.CharField(
        max_length=20, choices=RoleChoices.choices, default=RoleChoices.READER
    )
    issuer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="invitations",
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "drive_invitation"
        verbose_name = _("Item invitation")
        verbose_name_plural = _("Item invitations")
        constraints = [
            models.UniqueConstraint(
                fields=["email", "item"], name="email_and_item_unique_together"
            )
        ]

    def __str__(self):
        return f"{self.email} invited to {self.item}"

    def clean(self):
        """Validate fields."""
        super().clean()

        # Check if an identity already exists for the provided email
        if (
            User.objects.filter(email=self.email).exists()
            and not settings.OIDC_ALLOW_DUPLICATE_EMAILS
        ):
            raise ValidationError(
                {"email": [_("This email is already associated to a registered user.")]}
            )

    @property
    def is_expired(self):
        """Calculate if invitation is still valid or has expired."""
        if not self.created_at:
            return None

        validity_duration = timedelta(seconds=settings.INVITATION_VALIDITY_DURATION)
        return timezone.now() > (self.created_at + validity_duration)

    def get_abilities(self, user):
        """Compute and return abilities for a given user."""
        roles = []

        if user.is_authenticated:
            teams = user.teams
            try:
                roles = self.user_roles or []
            except AttributeError:
                try:
                    roles = self.item.accesses.filter(
                        models.Q(user=user) | models.Q(team__in=teams),
                    ).values_list("role", flat=True)
                except (self._meta.model.DoesNotExist, IndexError):
                    roles = []

        is_admin_or_owner = bool(
            set(roles).intersection({RoleChoices.OWNER, RoleChoices.ADMIN})
        )

        return {
            "destroy": is_admin_or_owner,
            "update": is_admin_or_owner,
            "partial_update": is_admin_or_owner,
            "retrieve": is_admin_or_owner,
        }
