"""
Declare and configure the models for the drive core application
"""
# pylint: disable=too-many-lines

import smtplib
import uuid
from datetime import timedelta
from enum import StrEnum
from logging import getLogger
from os.path import splitext

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GistIndex
from django.contrib.sites.models import Site
from django.core import mail, validators
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models, transaction
from django.db.models.expressions import RawSQL
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import get_language, override
from django.utils.translation import gettext_lazy as _

from django_ltree.functions import NLevel
from django_ltree.managers import TreeManager, TreeQuerySet
from django_ltree.models import TreeModel
from django_pydantic_field import SchemaField
from lasuite.drf.models.choices import (
    PRIVILEGED_ROLES,
    LinkReachChoices,
    LinkRoleChoices,
    RoleChoices,
    get_equivalent_link_definition,
)
from pydantic import BaseModel as PydanticBaseModel
from timezone_field import TimeZoneField

from core.permissions import get_permissions_backend
from core.storage.cache import invalidate_storage_used_cache
from core.utils.item_title import manage_unique_title as manage_unique_title_utils

logger = getLogger(__name__)

# Item fields whose update can change the storage used by a user.
STORAGE_USED_FIELDS = {"size", "creator", "creator_id", "hard_deleted_at", "quota_excluded"}


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


class ItemTypeChoices(models.TextChoices):
    """Defines the types of items that can be created."""

    FOLDER = "folder", _("Folder")
    FILE = "file", _("File")
    RESTRICTION = "restriction", _("Restriction")


class ItemUploadStateChoices(models.TextChoices):
    """Defines the possible states of an item."""

    PENDING = "pending", _("Pending")
    DUPLICATING = "duplicating", ("Duplicating")
    CONVERTING = "converting", _("Converting")
    ANALYZING = "analyzing", _("Analyzing")
    SUSPICIOUS = "suspicious", _("Suspicious")
    FILE_TOO_LARGE_TO_ANALYZE = (
        "file_too_large_to_analyze",
        _("File too large to analyze"),
    )
    READY = "ready", _("Ready")


class MirrorItemTaskStatusChoices(models.TextChoices):
    """Defines the possible statuses for a mirroring task."""

    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")


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
                    return self.get(email__iexact=email)
                except self.model.DoesNotExist:
                    pass
            elif (
                self.filter(email__iexact=email).exists()
                and not settings.OIDC_ALLOW_DUPLICATE_EMAILS
            ):
                raise DuplicateEmailError(
                    _(
                        "We couldn't find a user with this sub but the email is already "
                        "associated with a registered user."
                    )
                ) from err
        return None


class ColumnType(StrEnum):
    """Type of column allowed."""

    LAST_MODIFIED = "last_modified"
    CREATED = "created"
    CREATED_BY = "created_by"
    FILE_TYPE = "file_type"
    FILE_SIZE = "file_size"


class ColumnPreferences(PydanticBaseModel):
    """Pydantic model to validate the custom columns a user can have."""

    column1: ColumnType
    column2: ColumnType

    model_config = {"extra": "forbid"}


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
    short_name = models.CharField(_("short name"), max_length=100, null=True, blank=True)

    email = models.EmailField(_("identity email address"), blank=True, null=True)
    column_preferences = SchemaField(ColumnPreferences, blank=True, null=True, default=None)

    # Unlike the "email" field which stores the email coming from the OIDC token, this field
    # stores the email used by staff users to login to the admin site
    admin_email = models.EmailField(_("admin email address"), unique=True, blank=True, null=True)

    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default=None,
        verbose_name=_("language"),
        help_text=_("The language in which the user wants to see the interface."),
        null=True,
        blank=True,
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

    storage_limit_override = models.BigIntegerField(
        _("storage limit override"),
        help_text=_(
            "Storage limit in bytes for this user, used by the local entitlements "
            "backend. Leave empty to use the configured default limit. "
            "Set to 0 for unlimited storage."
        ),
        null=True,
        blank=True,
        default=None,
        validators=[validators.MinValueValidator(0)],
    )

    claims = models.JSONField(
        blank=True,
        default=dict,
        help_text=_("Claims from the OIDC token."),
    )

    last_release_note_seen = models.CharField(
        _("last release note seen"),
        max_length=85,
        blank=True,
        null=True,
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
            email__iexact=self.email,
            created_at__gte=(
                timezone.now() - timedelta(seconds=settings.INVITATION_VALIDITY_DURATION)
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
        # The bulk update bypasses Item.save() invalidating the
        # storage used cache.
        transaction.on_commit(lambda: invalidate_storage_used_cache([self.id]))

        valid_invitations.delete()

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Email this user."""
        if not self.email:
            raise ValueError("User has no email address.")
        mail.send_mail(subject, message, from_email, [self.email], **kwargs)

    def send_email(self, subject, context=None, language=None):
        """Generate and send email to the user from a template."""

        if not settings.EMAIL_HOST:
            logger.info("EMAIL_HOST host is not set, skipping email sending")
            return

        context = context or {}
        domain = settings.EMAIL_URL_APP or Site.objects.get_current().domain
        language = language or get_language()
        context.update(
            {
                "brandname": settings.EMAIL_BRAND_NAME,
                "domain": domain,
                "logo_img": settings.EMAIL_LOGO_IMG,
            }
        )

        with override(language):
            msg_html = render_to_string("mail/html/reconciliation.html", context)
            msg_plain = render_to_string("mail/text/reconciliation.txt", context)
            subject = str(subject)  # Force translation

            try:
                send_mail(
                    subject.capitalize(),
                    msg_plain,
                    settings.EMAIL_FROM,
                    [self.email],
                    html_message=msg_html,
                    fail_silently=False,
                )
            except smtplib.SMTPException as exception:
                logger.error("email to %s was not sent: %s", self.email, exception)

    @cached_property
    def teams(self):
        """
        Get list of teams in which the user is, as a list of strings.
        Must be cached if retrieved remotely.
        """
        return []


class UserReconciliation(BaseModel):
    """Model to run batch jobs to replace an active user by another one."""

    active_email = models.EmailField(_("Active email address"))
    inactive_email = models.EmailField(_("Email address to deactivate"))
    active_email_checked = models.BooleanField(default=False)
    inactive_email_checked = models.BooleanField(default=False)
    active_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="active_user",
    )
    inactive_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="inactive_user",
    )
    active_email_confirmation_id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, null=True
    )
    inactive_email_confirmation_id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, null=True
    )
    source_unique_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Unique ID in the source file"),
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", _("Pending")),
            ("ready", _("Ready")),
            ("done", _("Done")),
            ("error", _("Error")),
        ],
        default="pending",
    )
    logs = models.TextField(blank=True)

    class Meta:
        db_table = "drive_user_reconciliation"
        verbose_name = _("user reconciliation")
        verbose_name_plural = _("user reconciliations")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reconciliation from {self.inactive_email} to {self.active_email}"

    def save(self, *args, **kwargs):
        """
        For pending queries, identify the actual users and send validation emails.
        """
        if self.status == "pending":
            self.active_user = User.objects.filter(email=self.active_email).first()
            self.inactive_user = User.objects.filter(email=self.inactive_email).first()

            if self.active_user and self.inactive_user:
                if not self.active_email_checked:
                    self.send_reconciliation_confirm_email(
                        self.active_user, "active", self.active_email_confirmation_id
                    )
                if not self.inactive_email_checked:
                    self.send_reconciliation_confirm_email(
                        self.inactive_user,
                        "inactive",
                        self.inactive_email_confirmation_id,
                    )
                self.status = "ready"
            else:
                self.status = "error"
                self.logs = "Error: Both active and inactive users need to exist."

        super().save(*args, **kwargs)

    @transaction.atomic
    def process_reconciliation_request(self):
        """
        Process the reconciliation request as a transaction.

        - Transfer item accesses from inactive to active user, updating roles as needed.
        - Transfer item favorites from inactive to active user.
        - Transfer link traces from inactive to active user.
        - Reassign items created by the inactive user to the active user.
        - Reassign invitations issued by the inactive user to the active user.
        - Activate the active user and deactivate the inactive user.
        - Update the reconciliation entry itself.
        """

        # Prepare the data to perform the reconciliation on
        updated_accesses, removed_accesses = self.prepare_itemaccess_reconciliation()
        updated_linktraces, removed_linktraces = self.prepare_linktrace_reconciliation()
        updated_favorites, removed_favorites = self.prepare_itemfavorite_reconciliation()
        updated_items = self.prepare_item_creator_reconciliation()
        updated_invitations = self.prepare_invitation_issuer_reconciliation()

        self.active_user.is_active = True
        self.inactive_user.is_active = False

        # Actually perform the bulk operations
        ItemAccess.objects.bulk_update(updated_accesses, ["user", "role"])
        if removed_accesses:
            ids_to_delete = [entry.id for entry in removed_accesses]
            ItemAccess.objects.filter(id__in=ids_to_delete).delete()
            # Bulk delete bypasses ItemAccess.delete(), so the nb_accesses cache
            # of the affected items must be invalidated explicitly.
            items_to_invalidate = {entry.item_id: entry.item for entry in removed_accesses}
            for item in items_to_invalidate.values():
                item.invalidate_nb_accesses_cache()

        ItemFavorite.objects.bulk_update(updated_favorites, ["user"])
        if removed_favorites:
            ids_to_delete = [entry.id for entry in removed_favorites]
            ItemFavorite.objects.filter(id__in=ids_to_delete).delete()

        LinkTrace.objects.bulk_update(updated_linktraces, ["user"])
        if removed_linktraces:
            ids_to_delete = [entry.id for entry in removed_linktraces]
            LinkTrace.objects.filter(id__in=ids_to_delete).delete()

        Item.objects.bulk_update(updated_items, ["creator"])
        # The bulk update bypasses Item.save() invalidating the
        # storage used cache, and both users' usage change.
        transaction.on_commit(
            lambda: invalidate_storage_used_cache([self.active_user_id, self.inactive_user_id])
        )
        Invitation.objects.bulk_update(updated_invitations, ["issuer"])

        User.objects.bulk_update([self.active_user, self.inactive_user], ["is_active"])

        # Wrap up the reconciliation entry
        self.logs += (
            f"Requested update for {len(updated_accesses)} ItemAccess items "
            f"and deletion for {len(removed_accesses)} ItemAccess items.\n"
        )
        self.status = "done"
        self.save()

        self.send_reconciliation_done_email()

    def prepare_itemaccess_reconciliation(self):
        """
        Prepare the reconciliation by transferring item accesses from the inactive user
        to the active user.
        """
        updated_accesses = []
        removed_accesses = []
        inactive_accesses = ItemAccess.objects.filter(user=self.inactive_user)

        # Check items where the active user already has access
        inactive_accesses_items = inactive_accesses.values_list("item", flat=True)
        existing_accesses = ItemAccess.objects.filter(user=self.active_user).filter(
            item__in=inactive_accesses_items
        )
        existing_roles_per_item = dict(existing_accesses.values_list("item", "role"))

        for entry in inactive_accesses:
            if entry.item_id in existing_roles_per_item:
                # Update role if needed
                existing_role = existing_roles_per_item[entry.item_id]
                max_role = RoleChoices.max(entry.role, existing_role)
                if existing_role != max_role:
                    existing_access = existing_accesses.get(item=entry.item)
                    existing_access.role = max_role
                    updated_accesses.append(existing_access)
                removed_accesses.append(entry)
            else:
                entry.user = self.active_user
                updated_accesses.append(entry)

        return updated_accesses, removed_accesses

    def prepare_itemfavorite_reconciliation(self):
        """
        Prepare the reconciliation by transferring item favorites from the inactive user
        to the active user.
        """
        updated_favorites = []
        removed_favorites = []

        existing_favorites = ItemFavorite.objects.filter(user=self.active_user)
        existing_favorite_item_ids = set(existing_favorites.values_list("item_id", flat=True))

        inactive_favorites = ItemFavorite.objects.filter(user=self.inactive_user)

        for entry in inactive_favorites:
            if entry.item_id in existing_favorite_item_ids:
                removed_favorites.append(entry)
            else:
                entry.user = self.active_user
                updated_favorites.append(entry)

        return updated_favorites, removed_favorites

    def prepare_linktrace_reconciliation(self):
        """
        Prepare the reconciliation by transferring link traces from the inactive user
        to the active user.
        """
        updated_linktraces = []
        removed_linktraces = []

        existing_linktraces = LinkTrace.objects.filter(user=self.active_user)
        inactive_linktraces = LinkTrace.objects.filter(user=self.inactive_user)

        for entry in inactive_linktraces:
            if existing_linktraces.filter(item=entry.item).exists():
                removed_linktraces.append(entry)
            else:
                entry.user = self.active_user
                updated_linktraces.append(entry)

        return updated_linktraces, removed_linktraces

    def prepare_item_creator_reconciliation(self):
        """
        Prepare the reconciliation by reassigning items created by the inactive user
        to the active user.
        """
        updated_items = []

        inactive_items = Item.objects.filter(creator=self.inactive_user)

        for entry in inactive_items:
            entry.creator = self.active_user
            updated_items.append(entry)

        return updated_items

    def prepare_invitation_issuer_reconciliation(self):
        """
        Prepare the reconciliation by reassigning invitations issued by the inactive user
        to the active user.
        """
        updated_invitations = []

        inactive_invitations = Invitation.objects.filter(issuer=self.inactive_user)

        for entry in inactive_invitations:
            entry.issuer = self.active_user
            updated_invitations.append(entry)

        return updated_invitations

    def send_reconciliation_confirm_email(self, user, user_type, confirmation_id, language=None):
        """Method allowing to send confirmation email for reconciliation requests."""
        language = language or get_language()
        domain = settings.EMAIL_URL_APP or Site.objects.get_current().domain

        message = _(
            """You have requested a reconciliation of your user accounts on Drive.
            To confirm that you are the one who initiated the request
            and that this email belongs to you:"""
        )

        with override(language):
            subject = _("Confirm by clicking the link to start the reconciliation")
            context = {
                "title": subject,
                "message": message,
                "link": f"{domain}/user-reconciliations/{user_type}/{confirmation_id}/",
                "link_label": str(_("Click here")),
                "button_label": str(_("Confirm")),
            }

        user.send_email(subject, context, language)

    def send_reconciliation_done_email(self, language=None):
        """Method allowing to send done email for reconciliation requests."""
        language = language or get_language()
        domain = settings.EMAIL_URL_APP or Site.objects.get_current().domain

        message = _(
            """Your reconciliation request has been processed.
            New documents are likely associated with your account:"""
        )

        with override(language):
            subject = _("Your accounts have been merged")
            context = {
                "title": subject,
                "message": message,
                "link": f"{domain}/",
                "link_label": str(_("Click here to see")),
                "button_label": str(_("See my documents")),
            }

        self.active_user.send_email(subject, context, language)


class UserReconciliationCsvImport(BaseModel):
    """Model to import reconciliation requests from an external source."""

    file = models.FileField(upload_to="imports/", verbose_name=_("CSV file"))
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", _("Pending")),
            ("running", _("Running")),
            ("done", _("Done")),
            ("error", _("Error")),
        ],
        default="pending",
    )
    logs = models.TextField(blank=True)

    class Meta:
        db_table = "drive_user_reconciliation_csv_import"
        verbose_name = _("user reconciliation CSV import")
        verbose_name_plural = _("user reconciliation CSV imports")

    def __str__(self):
        return f"User reconciliation CSV import {self.id}"

    def send_email(self, subject, emails, context=None, language=None):
        """Generate and send email to the user from a template."""

        if not settings.EMAIL_HOST:
            logger.debug("EMAIL_HOST host is not set, skipping email sending")
            return

        context = context or {}
        domain = settings.EMAIL_URL_APP or Site.objects.get_current().domain
        language = language or get_language()
        context.update(
            {
                "brandname": settings.EMAIL_BRAND_NAME,
                "domain": domain,
                "logo_img": settings.EMAIL_LOGO_IMG,
            }
        )

        with override(language):
            msg_html = render_to_string("mail/html/reconciliation.html", context)
            msg_plain = render_to_string("mail/text/reconciliation.txt", context)
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
                logger.error("email to %s was not sent: %s", emails, exception)

    def send_reconciliation_error_email(self, recipient_email, other_email, language=None):
        """Method allowing to send email for reconciliation requests with errors."""
        language = language or get_language()

        emails = [recipient_email]

        message = _(
            """Your request for reconciliation was unsuccessful.
            Reconciliation failed for the following email addresses:
            {recipient_email}, {other_email}.
            Please check for typos.
            You can submit another request with the valid email addresses."""
        ).format(recipient_email=recipient_email, other_email=other_email)

        with override(language):
            subject = _("Reconciliation of your Drive accounts not completed")
            context = {
                "title": subject,
                "message": message,
                "link": settings.USER_RECONCILIATION_FORM_URL,
                "link_label": str(_("Click here")),
                "button_label": str(_("Make a new request")),
            }

        self.send_email(subject, emails, context, language)


class AnnotateUserRoleQuerySetMixin:
    """Mixin to use in a QuerySet to add user_roles annotation."""

    def annotate_user_roles(self, user):
        """
        Annotate queryset with the roles of the current user
        on the item or its ancestors.
        """
        output_field = ArrayField(base_field=models.CharField())

        if user.is_authenticated:
            user_roles_subquery = ItemAccess.objects.filter(
                models.Q(user=user) | models.Q(team__in=user.teams),
                item__path__ancestors=models.OuterRef(self.path_property),
            ).values_list("role", flat=True)

            return self.annotate(
                user_roles=models.Func(
                    user_roles_subquery, function="ARRAY", output_field=output_field
                )
            )

        return self.annotate(
            user_roles=models.Value([], output_field=output_field),
        )


class ItemQuerySet(AnnotateUserRoleQuerySetMixin, TreeQuerySet):
    """Custom queryset for Item model with additional methods."""

    path_property = "path"

    def annotate_has_restriction(self):
        """Annotate whether a restriction targets each item."""
        return self.annotate(
            has_restriction=models.Exists(self.model.objects.filter(target=models.OuterRef("pk")))
        )

    def readable_per_se(self, user):
        """
        Filters the queryset to return documents that the given user has
        permission to read.
        :param user: The user for whom readable documents are to be fetched.
        :return: A queryset of documents readable by the user.
        """
        if user.is_authenticated:
            return self.filter(
                models.Q(accesses__user=user)
                | models.Q(accesses__team__in=user.teams)
                | ~models.Q(link_reach=LinkReachChoices.RESTRICTED)
            )

        return self.filter(models.Q(link_reach=LinkReachChoices.PUBLIC))

    def filter_non_deleted(self, **kwargs):
        """Filter the non deleted items"""
        return self.filter(
            models.Q(
                models.Q(deleted_at__isnull=True) | models.Q(ancestors_deleted_at__isnull=True),
            ),
            **kwargs,
        )

    def created_by(self, user):
        """Filter items created by the given user."""
        return self.filter(creator=user)

    def not_created_by(self, user):
        """Filter items created by someone other than the given user."""
        return self.exclude(creator=user)

    def favorited_by(self, user):
        """Filter items the given user marked as favorite."""
        favorite = ItemFavorite.objects.filter(item_id=models.OuterRef("pk"), user=user)
        return self.filter(models.Exists(favorite))

    def not_favorited_by(self, user):
        """Filter items the given user did not mark as favorite."""
        favorite = ItemFavorite.objects.filter(item_id=models.OuterRef("pk"), user=user)
        return self.exclude(models.Exists(favorite))

    def owned_by(self, user):
        """Filter items the given user owns, directly or through an ancestor access."""
        owner_access = ItemAccess.objects.filter(
            models.Q(user=user) | models.Q(team__in=user.teams),
            role=RoleChoices.OWNER,
            item__path__ancestors=models.OuterRef("path"),
        )
        return self.filter(models.Exists(owner_access))

    def annotate_is_favorite(self, user):
        """
        Annotate item queryset with the favorite status for the current user.
        """
        if user.is_authenticated:
            favorite_exists_subquery = ItemFavorite.objects.filter(
                item_id=models.OuterRef("pk"), user=user
            )
            return self.annotate(is_favorite=models.Exists(favorite_exists_subquery))

        return self.annotate(is_favorite=models.Value(False))

    def annotate_user_roles(self, user):
        """
        Annotate item queryset with the roles of the current user
        on the item or its ancestors.
        """
        output_field = ArrayField(base_field=models.CharField())

        if user.is_authenticated:
            user_roles_subquery = ItemAccess.objects.filter(
                models.Q(user=user) | models.Q(team__in=user.teams),
                item__path__ancestors=models.OuterRef("path"),
            ).values_list("role", flat=True)

            return self.annotate(
                user_roles=models.Func(
                    user_roles_subquery, function="ARRAY", output_field=output_field
                )
            )

        return self.annotate(
            user_roles=models.Value([], output_field=output_field),
        )

    def annotate_with_numchild(self):
        """
        Annotate queryset with the count of direct non-deleted children (_numchild)
        and folder children (_numchild_folder).
        Uses two correlated subqueries; the Item.numchild property reads these annotations.
        """
        direct_children_qs = (
            Item.objects.filter(
                path__descendants=models.OuterRef("path"),
                deleted_at__isnull=True,
                ancestors_deleted_at__isnull=True,
            )
            .annotate(_depth_diff=NLevel("path") - NLevel(models.OuterRef("path")))
            .filter(_depth_diff=1)
            .order_by()
        )

        numchild_sq = models.Subquery(
            # .values(group_key=...) introduces a GROUP BY on a constant, collapsing
            # all rows into a single aggregate row so that the subsequent .annotate()
            # produces exactly one COUNT value — the scalar the Subquery expects.
            # Without it, Django would emit no GROUP BY and the ORM would raise an
            # error because COUNT appears without a matching group expression.
            direct_children_qs.values(group_key=models.Value(1))
            .annotate(count=models.Count("pk"))
            .values("count"),
            output_field=models.IntegerField(),
        )

        numchild_folder_sq = models.Subquery(
            direct_children_qs.filter(type=ItemTypeChoices.FOLDER)
            .values(group_key=models.Value(1))
            .annotate(count=models.Count("pk"))
            .values("count"),
            output_field=models.IntegerField(),
        )

        return self.annotate(
            _numchild=numchild_sq,
            _numchild_folder=numchild_folder_sq,
        )


class ItemManager(TreeManager.from_queryset(ItemQuerySet)):
    """Custom manager for Item model overriding create_child method."""

    def get_queryset(self):
        """Get the queryset for the Item model."""
        return ItemQuerySet(model=self.model, using=self._db)

    def readable_per_se(self, user):
        """
        Filters documents based on user permissions using the custom queryset.
        :param user: The user for whom readable documents are to be fetched.
        :return: A queryset of documents readable by the user.
        """
        return self.get_queryset().readable_per_se(user)

    def create_child(self, parent=None, **kwargs):
        """
        Check if the item can have children before adding one and if the title is
        unique in the same path.
        """
        if parent:
            if parent.type != ItemTypeChoices.FOLDER:
                raise ValidationError(
                    {
                        "type": ValidationError(
                            _("Only folders can have children."),
                            code="item_create_child_type_folder_only",
                        )
                    }
                )
            kwargs["title"] = manage_unique_title_utils(
                self.children(parent.path), kwargs.get("title")
            )

        if not kwargs.get("id"):
            kwargs["id"] = str(uuid.uuid4())

        kwargs["path"] = str(kwargs["id"])

        if parent:
            kwargs["path"] = f"{parent.path!s}.{kwargs['id']!s}"

        item = self.create(**kwargs)

        return item


# pylint: disable=too-many-public-methods,too-many-instance-attributes
class Item(TreeModel, BaseModel):
    """Item in the tree."""

    title = models.CharField(_("title"), max_length=255)
    link_reach = models.CharField(
        max_length=20,
        choices=LinkReachChoices.choices,
        null=True,
        blank=True,
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
    hard_deleted_at = models.DateTimeField(null=True, blank=True)

    filename = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(
        max_length=30,
        choices=ItemTypeChoices.choices,
        default=ItemTypeChoices.FOLDER,
    )
    upload_state = models.CharField(
        max_length=25,
        choices=ItemUploadStateChoices.choices,
        null=True,
        blank=True,
    )
    mimetype = models.CharField(max_length=255, null=True, blank=True)
    target = models.OneToOneField(
        "self",
        on_delete=models.CASCADE,
        related_name="restriction",
        null=True,
        blank=True,
    )
    main_workspace = models.BooleanField(default=False)
    size = models.BigIntegerField(null=True, blank=True)
    quota_excluded = models.BooleanField(
        default=False,
        help_text=_("Exclude this item from its creator's storage quota computation."),
    )
    description = models.TextField(null=True, blank=True)
    malware_detection_info = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text=_("Malware detection info when the analysis status is unsafe."),
    )

    label_size = 7

    objects = ItemManager()

    class Meta:
        db_table = "drive_item"
        verbose_name = _("Item")
        verbose_name_plural = _("Items")
        ordering = ("created_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(deleted_at__isnull=True)
                    | models.Q(deleted_at=models.F("ancestors_deleted_at"))
                ),
                name="check_deleted_at_matches_ancestors_deleted_at_when_set",
            ),
            models.CheckConstraint(
                condition=(
                    (models.Q(type=ItemTypeChoices.RESTRICTION) & models.Q(target__isnull=False))
                    | (~models.Q(type=ItemTypeChoices.RESTRICTION) & models.Q(target__isnull=True))
                ),
                name="check_target_only_on_restrictions",
            ),
        ]
        indexes = [
            GistIndex(fields=["path"]),
            models.Index(NLevel(models.F("path")), name="drive_item_path_nlevel_idx"),
            # Covers the storage used computation by creator.
            models.Index(
                fields=["creator"],
                include=["size"],
                condition=models.Q(hard_deleted_at__isnull=True, quota_excluded=False),
                name="item_creator_size_quota_idx",
            ),
        ]

    def __str__(self):
        return str(self.title)

    def __init__(self, *args, **kwargs):
        """Initialize cache property."""
        super().__init__(*args, **kwargs)
        self._ancestors_link_definition = None
        self._computed_link_definition = None

    def save(self, *args, **kwargs):
        """Set the upload state to pending if it's the first save and it's a file"""
        # Validate filename requirements based on item type
        if self.type == ItemTypeChoices.FILE:
            if self.filename is None:
                raise ValidationError(
                    {
                        "filename": ValidationError(
                            _("Filename is required for files."),
                            code="item_filename_required_for_files",
                        )
                    }
                )
        elif self.filename is not None:
            raise ValidationError(
                {
                    "filename": ValidationError(
                        _("Filename is only allowed for files."),
                        code="item_filename_only_allowed_for_files",
                    )
                }
            )

        if (
            self.created_at is None
            and self.type == ItemTypeChoices.FILE
            and self.upload_state
            not in (
                ItemUploadStateChoices.DUPLICATING,
                ItemUploadStateChoices.CONVERTING,
            )
        ):
            self.upload_state = ItemUploadStateChoices.PENDING

        if not self.path:
            self.path = str(self.id)

        super().save(*args, **kwargs)

        self._invalidate_storage_used_cache(kwargs.get("update_fields"))

    def _invalidate_storage_used_cache(self, update_fields):
        """
        Invalidate the creator's cached storage usage when a save may have
        changed it. Bulk queryset updates bypass save() and must invalidate
        the cache explicitly.
        """
        if update_fields and STORAGE_USED_FIELDS.isdisjoint(update_fields):
            return
        if not self.creator_id:
            return
        transaction.on_commit(lambda: invalidate_storage_used_cache([self.creator_id]))

    def delete(self, using=None, keep_parents=False):
        if self.deleted_at is None and self.ancestors_deleted_at is None:
            raise RuntimeError("The item must be soft deleted before being deleted.")

        return super().delete(using, keep_parents)

    def ancestors(self):
        """Return the ancestors of the item excluding the item itself."""
        return super().ancestors().exclude(id=self.id)

    def descendants(self):
        """Return the descendants of the item excluding the item itself."""
        return super().descendants().exclude(id=self.id)

    @property
    def extension(self):
        """Return the extension related to the filename."""
        if self.filename is None:
            raise RuntimeError("The item must have a filename to compute its extension.")

        _, extension = splitext(self.filename)

        if extension:
            return extension.lstrip(".")

        return None

    @property
    def key_base(self):
        """Key base of the location where the item is stored in object storage."""
        if not self.pk:
            raise RuntimeError("The item instance must be saved before requesting a storage key.")

        if self.type != ItemTypeChoices.FILE:
            raise RuntimeError("Only files have a storage key.")

        return f"item/{self.pk!s}"

    @property
    def file_key(self):
        """Key used to store the file in object storage."""
        if self.filename is None:
            raise RuntimeError("The item must have a filename to generate a file key.")

        return f"{self.key_base}/{self.filename}"

    @property
    def depth(self):
        """Return the depth of the item in the tree."""
        return len(self.path)

    def get_nb_accesses_cache_key(self):
        """Generate a unique cache key for each item."""
        return f"item_{self.id!s}_nb_accesses"

    def manage_unique_title(self, title):
        """Manage the unique title in the same path."""
        return manage_unique_title_utils(
            self.siblings(),
            title,
        )

    @property
    def nb_accesses(self):
        """Calculate the number of accesses."""
        try:
            return self._nb_accesses
        except AttributeError:
            cache_key = self.get_nb_accesses_cache_key()
            nb_accesses = cache.get(cache_key)

            if nb_accesses is None:
                nb_accesses = get_permissions_backend().effective_accesses(self).count()
                cache.set(cache_key, nb_accesses)

            return nb_accesses

    @property
    def numchild(self):
        """Return the number of non-deleted children from annotation."""
        return self._numchild  # pylint: disable=no-member

    @property
    def numchild_folder(self):
        """Calculate the number of non-deleted folder children from annotation."""
        return self._numchild_folder  # pylint: disable=no-member

    @property
    def is_root(self):
        """Return True if the item is the root of the tree."""
        return len(self.path) == 1

    @property
    def is_restricted(self):
        """Return whether a restriction targets this folder."""
        if (annotated := getattr(self, "has_restriction", None)) is not None:
            return annotated
        return self._meta.model.objects.filter(target=self).exists()

    def get_root(self):
        """Return the root of the tree."""
        return self.ancestors().filter(path__depth=1).first()

    def parent(self):
        """Return the direct parent, looked up by its exact path."""
        if len(self.path) > 1:
            return self._meta.model.objects.filter(path=str(self.path[:-1])).first()
        return None

    def invalidate_nb_accesses_cache(self):
        """
        Invalidate the cache for number of accesses, including on affected descendants.
        """
        for item in self._meta.model.objects.filter(path__descendants=self.path).only("id"):
            cache_key = item.get_nb_accesses_cache_key()
            cache.delete(cache_key)

    def get_role(self, user):
        """Return the role a user has on an item."""
        if not user.is_authenticated:
            return None

        try:
            roles = self.user_roles or []
        except AttributeError:
            roles = get_permissions_backend().roles_for(user, self)

        return RoleChoices.max(*roles)

    def compute_ancestors_links_paths_mapping(self):
        """
        Compute the ancestors links for the current item up to the highest readable ancestor.
        """
        ancestors = (
            (self.ancestors() | self._meta.model.objects.filter(pk=self.pk))
            .filter(ancestors_deleted_at__isnull=True)
            .order_by("path")
        )
        ancestors_links = []
        paths_links_mapping = {}

        for ancestor in ancestors:
            ancestors_links.append(
                {"link_reach": ancestor.link_reach, "link_role": ancestor.link_role}
            )
            paths_links_mapping[str(ancestor.path)] = ancestors_links.copy()

        return paths_links_mapping

    @property
    def link_definition(self):
        """Returns link reach/role as a definition in dictionary format."""
        return {"link_reach": self.link_reach, "link_role": self.link_role}

    @property
    def ancestors_link_definition(self):
        """Link definition equivalent to all document's ancestors."""
        if getattr(self, "_ancestors_link_definition", None) is None:
            if self.depth <= 1:
                ancestors_links = []
            else:
                mapping = self.compute_ancestors_links_paths_mapping()
                ancestors_links = mapping.get(str(self.path[:-1]), [])
            self._ancestors_link_definition = get_equivalent_link_definition(ancestors_links)

        return self._ancestors_link_definition

    @ancestors_link_definition.setter
    def ancestors_link_definition(self, definition):
        """Cache the ancestors_link_definition."""
        self._ancestors_link_definition = definition

    @property
    def ancestors_link_reach(self):
        """Link reach equivalent to all document's ancestors."""
        return self.ancestors_link_definition["link_reach"]

    @property
    def ancestors_link_role(self):
        """Link role equivalent to all document's ancestors."""
        return self.ancestors_link_definition["link_role"]

    @property
    def computed_link_definition(self):
        """
        Link reach/role on the document, combining inherited ancestors' link
        definitions and the document's own link definition.
        """
        if getattr(self, "_computed_link_definition", None) is None:
            self._computed_link_definition = get_equivalent_link_definition(
                [self.ancestors_link_definition, self.link_definition]
            )
        return self._computed_link_definition

    @property
    def computed_link_reach(self):
        """Actual link reach on the document."""
        return self.computed_link_definition["link_reach"]

    @property
    def computed_link_role(self):
        """Actual link role on the document."""
        return self.computed_link_definition["link_role"]

    def get_abilities(self, user):
        """Compute and return abilities for a given user on the item."""
        return get_permissions_backend().abilities(user, self)

    def send_email(self, subject, emails, context=None, language=None):
        """Generate and send email from a template."""

        if not settings.EMAIL_HOST:
            logger.debug("EMAIL_HOST host is not set, skipping email sending")
            return

        context = context or {}
        base_url = settings.EMAIL_URL_APP or Site.objects.get_current().domain
        language = language or get_language()
        context.update(
            {
                "brandname": settings.EMAIL_BRAND_NAME,
                "item": self,
                "domain": base_url,
                "link": (
                    f"{base_url}/explorer/items/files/{self.id}/"
                    if self.type == ItemTypeChoices.FILE
                    else f"{base_url}/explorer/items/{self.id}/"
                ),
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
            f"{sender.full_name:s} ({sender.email})" if sender.full_name else sender.email
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
        if self.ancestors().filter(deleted_at__isnull=False).exists():
            raise RuntimeError(
                "Cannot delete this item because one or more ancestors are already deleted."
            )

        self.ancestors_deleted_at = self.deleted_at = timezone.now()

        self.save(update_fields=["deleted_at", "ancestors_deleted_at"])

        # Mark all descendants as soft deleted
        if self.type == ItemTypeChoices.FOLDER:
            self.descendants().filter(ancestors_deleted_at__isnull=True).update(
                ancestors_deleted_at=self.ancestors_deleted_at,
            )

    def hard_delete(self):
        """
        Hard delete the item, marking the deletion on descendants.
        We still keep the .delete() method untouched for programmatic purposes.
        """
        if self.hard_deleted_at:
            raise ValidationError(
                {
                    "hard_deleted_at": ValidationError(
                        _("This item is already hard deleted."),
                        code="item_hard_delete_already_effective",
                    )
                }
            )

        if self.deleted_at is None:
            raise ValidationError(
                {
                    "hard_deleted_at": ValidationError(
                        _("To hard delete an item, it must first be soft deleted."),
                        code="item_hard_delete_should_soft_delete_first",
                    )
                }
            )

        # Collect the creators impacted before marking the tree as hard deleted:
        # descendants can have different creators and their bulk update below
        # bypasses Item.save() invalidating the storage used cache.
        creator_ids = set(
            self.descendants()
            .filter(hard_deleted_at__isnull=True)
            .values_list("creator_id", flat=True)
        )
        creator_ids.add(self.creator_id)

        self.hard_deleted_at = timezone.now()
        self.save(update_fields=["hard_deleted_at"])

        # Mark all descendants as hard deleted
        self.descendants().update(hard_deleted_at=self.hard_deleted_at)

        transaction.on_commit(lambda: invalidate_storage_used_cache(creator_ids))

    @transaction.atomic
    def restore(self):
        """Cancelling a soft delete with checks."""
        # This should not happen
        if self.deleted_at is None:
            raise ValidationError(
                {
                    "deleted_at": ValidationError(
                        _("This item is not deleted."),
                        code="item_restore_not_deleted",
                    )
                }
            )

        if (
            self.deleted_at < get_trashbin_cutoff()
            or Item.objects.filter(
                path__ancestors=self.path,
                hard_deleted_at__isnull=False,
            ).exists()
        ):
            raise ValidationError(
                {
                    "deleted_at": ValidationError(
                        _("This item was permanently deleted and cannot be restored."),
                        code="item_restore_hard_deleted",
                    )
                }
            )

        # save the current deleted_at value to exclude it from the descendants update
        current_deleted_at = self.deleted_at
        has_ancestors_deleted = False

        if self.depth > 1:
            has_ancestors_deleted = self.ancestors().filter(deleted_at__isnull=False).exists()

            if has_ancestors_deleted:
                # if it has ancestors deleted, try to move it to the top level ancestor
                highest_ancestor = self.ancestors().filter(path__depth=1).get()
                self.move(highest_ancestor)

        # Restore the current item
        self.deleted_at = None
        self.ancestors_deleted_at = None

        self.save(update_fields=["deleted_at", "ancestors_deleted_at"])

        self.descendants().exclude(
            models.Q(deleted_at__isnull=False)
            | models.Q(ancestors_deleted_at__lt=current_deleted_at)
        ).update(ancestors_deleted_at=None)

    @transaction.atomic
    def move(self, target):
        """
        Move an item to a new position in the tree.
        """
        if target and target.type != ItemTypeChoices.FOLDER:
            raise ValidationError(
                {
                    "target": ValidationError(
                        _("Only folders can be targeted when moving an item"),
                        code="item_move_target_not_a_folder",
                    )
                }
            )

        if self.is_restricted:
            raise ValidationError(
                {
                    "target": ValidationError(
                        _("A restricted folder cannot be moved"),
                        code="item_move_restricted",
                    )
                }
            )

        if (
            self.type == ItemTypeChoices.RESTRICTION
            and target
            and str(target.path).startswith(str(self.target.path))
        ):
            raise ValidationError(
                {
                    "target": ValidationError(
                        _("A restriction cannot be moved under its own target"),
                        code="item_move_restriction_under_target",
                    )
                }
            )

        old_path = self.path
        if target:
            self.path = f"{target.path!s}.{self.id!s}"
        else:
            self.path = str(self.id)

        self.save(update_fields=["path"])

        if self.type == ItemTypeChoices.FOLDER:
            # https://patshaughnessy.net/2017/12/14/manipulating-trees-using-sql-and-the-postgres-ltree-extension
            self._meta.model.objects.filter(path__descendants=old_path).update(
                path=RawSQL("%s || subpath(path, nlevel(%s))", (str(self.path), str(old_path)))
            )

    @transaction.atomic
    def restrict(self, user):
        """Restrict the folder by detaching it to the tree root behind a restriction."""
        item = self._meta.model.objects.select_for_update().get(pk=self.pk)

        if item.type != ItemTypeChoices.FOLDER:
            raise ValidationError(
                {
                    "is_restricted": ValidationError(
                        _("Only folders can be restricted"),
                        code="item_restrict_type_folder_only",
                    )
                }
            )
        if item.is_restricted:
            raise ValidationError(
                {
                    "is_restricted": ValidationError(
                        _("This folder is already restricted"),
                        code="item_restrict_already_restricted",
                    )
                }
            )
        if item.depth == 1:
            raise ValidationError(
                {
                    "is_restricted": ValidationError(
                        _("A root folder cannot be restricted"),
                        code="item_restrict_root",
                    )
                }
            )
        if item.ancestors_deleted_at:
            raise ValidationError(
                {
                    "is_restricted": ValidationError(
                        _("A deleted folder cannot be restricted"),
                        code="item_restrict_deleted",
                    )
                }
            )
        if item.get_role(user) != RoleChoices.OWNER:
            raise ValidationError(
                {
                    "is_restricted": ValidationError(
                        _("Only owners can restrict a folder"),
                        code="item_restrict_owner_only",
                    )
                }
            )

        parent = item.parent()

        ItemAccess.objects.update_or_create(
            item=item, user=user, defaults={"role": RoleChoices.OWNER}
        )

        item.move(None)

        if item.link_reach is None:
            item.link_reach = LinkReachChoices.RESTRICTED
            item.save(update_fields=["link_reach", "updated_at"])

        self._meta.model.objects.create_child(
            parent=parent,
            creator=user,
            type=ItemTypeChoices.RESTRICTION,
            target=item,
            title=item.title,
        )
        item.invalidate_nb_accesses_cache()

        return item

    def _normalize_explicit_accesses(self):
        """Delete explicit accesses inferior or equal to the inherited role."""
        inherited_accesses = (
            ItemAccess.objects.filter(item__path__ancestors=self.path)
            .exclude(item=self)
            .values_list("user_id", "team", "role")
        )
        inherited_roles = {}
        for user_id, team, role in inherited_accesses:
            key = (user_id, team)
            inherited_roles[key] = RoleChoices.max(inherited_roles.get(key), role)

        redundant_ids = [
            access.id
            for access in ItemAccess.objects.filter(item=self)
            if RoleChoices.get_priority(access.role)
            <= RoleChoices.get_priority(inherited_roles.get((access.user_id, access.team)))
        ]
        if redundant_ids:
            ItemAccess.objects.filter(id__in=redundant_ids).delete()

    def _normalize_explicit_link_reach(self):
        """Reset the link reach to inherit when inferior or equal to the inherited one."""
        # The cached ancestors definition predates the move, recompute it
        self._ancestors_link_definition = None
        inherited_reach = self.ancestors_link_definition["link_reach"]
        if LinkReachChoices.get_priority(self.link_reach) <= LinkReachChoices.get_priority(
            inherited_reach
        ):
            self.link_reach = None
            self.save(update_fields=["link_reach", "updated_at"])

    @transaction.atomic
    def unrestrict(self):
        """Lift restriction and reattach the folder at the restriction's location."""
        item = self._meta.model.objects.select_for_update().get(pk=self.pk)

        restriction = self._meta.model.objects.select_for_update().filter(target=item).first()
        if restriction is None:
            raise ValidationError(
                {
                    "is_restricted": ValidationError(
                        _("This folder is not restricted"),
                        code="item_unrestrict_not_restricted",
                    )
                }
            )

        parent = None
        if restriction.ancestors_deleted_at is None:
            parent = restriction.parent()
        self._meta.model.objects.filter(pk=restriction.pk).delete()

        if parent:
            item.title = manage_unique_title_utils(
                self._meta.model.objects.children(parent.path), item.title
            )
            item.save(update_fields=["title", "updated_at"])
            item.move(parent)
            item._normalize_explicit_accesses()  # noqa: SLF001  # pylint: disable=protected-access
            item._normalize_explicit_link_reach()  # noqa: SLF001  # pylint: disable=protected-access

        item.invalidate_nb_accesses_cache()

        return item


class MirrorItemTask(BaseModel):
    """Model managing a status for a mirroring task."""

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="mirror_tasks",
    )
    status = models.CharField(
        max_length=25,
        choices=MirrorItemTaskStatusChoices.choices,
        default=MirrorItemTaskStatusChoices.PENDING,
    )
    error_details = models.TextField(null=True, blank=True)
    retries = models.IntegerField(default=0)

    class Meta:
        db_table = "drive_mirror_item_task"
        verbose_name = _("Mirror item task")
        verbose_name_plural = _("Mirror item tasks")

    def __str__(self):
        return f"Mirror task for item {self.item!s} with status {self.status!s}"


class LinkTrace(BaseModel):
    """
    Relation model to trace accesses to an item via a link by a logged-in user.
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
                violation_error_message=_("A link trace already exists for this item/user."),
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_items")

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


class ItemAccessQuerySet(AnnotateUserRoleQuerySetMixin, models.QuerySet):
    """Custom queryset for ItemAccess model with additional methods."""

    path_property = "item__path"


class ItemAccessManager(models.Manager.from_queryset(ItemAccessQuerySet)):
    """Manager for ItemAccess model."""


class ItemAccess(BaseModel):
    """Relation model to give access to an item for a user or a team with a role."""

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="accesses",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    team = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.READER)

    objects = ItemAccessManager()

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

    @property
    def target_key(self):
        """Get a unique key for the actor targeted by the access, without possible conflict."""
        return f"user:{self.user_id!s}" if self.user_id else f"team:{self.team:s}"

    def _compute_max_ancestors_role(self):
        """
        Compute the max ancestors role for this instance.
        and return a tuple of (max_ancestors_role, item_id)
        """
        ancestors = self.item.ancestors().filter(ancestors_deleted_at__isnull=True)
        filter_condition = models.Q()
        if self.user:
            filter_condition |= models.Q(user=self.user)
        if self.team:
            filter_condition |= models.Q(team=self.team)
        ancestors_roles = ItemAccess.objects.filter(
            filter_condition, item__in=ancestors
        ).values_list("role", "item_id")

        roles = dict(ancestors_roles)

        max_role = RoleChoices.max(*roles.keys())

        self._max_ancestors_role = max_role
        self._max_ancestors_role_item_id = roles.get(max_role)

    @property
    def max_ancestors_role(self):
        """Link definition equivalent to all document's ancestors."""
        try:
            return self._max_ancestors_role
        except AttributeError:
            pass

        self._compute_max_ancestors_role()

        return self._max_ancestors_role

    @property
    def max_ancestors_role_item_id(self):
        """Get the item_id of the item with the max ancestors role."""
        try:
            return self._max_ancestors_role_item_id
        except AttributeError:
            pass

        self._compute_max_ancestors_role()

        return self._max_ancestors_role_item_id

    @max_ancestors_role.setter
    def max_ancestors_role(self, max_ancestors_role):
        """Cache the max_ancestors_role."""
        self._max_ancestors_role = max_ancestors_role

    @max_ancestors_role_item_id.setter
    def max_ancestors_role_item_id(self, max_ancestors_role_item_id):
        """Cache the max_ancestors_role_item_id."""
        self._max_ancestors_role_item_id = max_ancestors_role_item_id

    def get_role(self, user):
        """Return the role a user has on an item related to this access.."""
        if not user.is_authenticated:
            return None

        try:
            roles = self.user_roles or []
        except AttributeError:
            roles = ItemAccess.objects.filter(
                models.Q(user=user) | models.Q(team__in=user.teams),
                item__path__ancestors=self.item.path,
            ).values_list("role", flat=True)

        return RoleChoices.max(*roles)

    def get_abilities(self, user, is_explicit=True):
        """
        Compute and return abilities for a given user on the item access.
        """
        user_role = self.get_role(user)
        is_owner_or_admin = user_role in PRIVILEGED_ROLES

        if self.role == RoleChoices.OWNER:
            can_delete = user_role == RoleChoices.OWNER and (
                # check if item is not root trying to avoid an extra query
                self.item.depth > 1
                or ItemAccess.objects.filter(item_id=self.item_id, role=RoleChoices.OWNER).count()
                > 1
            )
            set_role_to = RoleChoices.values if can_delete else []
        else:
            can_delete = is_owner_or_admin
            set_role_to = []
            if is_owner_or_admin:
                set_role_to.extend([RoleChoices.READER, RoleChoices.EDITOR, RoleChoices.ADMIN])
            if user_role == RoleChoices.OWNER:
                set_role_to.append(RoleChoices.OWNER)

        ancestors_role_priority = RoleChoices.get_priority(self.max_ancestors_role)
        if is_explicit:
            # Filter out roles that would be lower than the one the user already has
            set_role_to = [
                candidate_role
                for candidate_role in set_role_to
                if RoleChoices.get_priority(candidate_role) >= ancestors_role_priority
            ]
        else:
            set_role_to = [
                candidate_role
                for candidate_role in set_role_to
                if RoleChoices.get_priority(candidate_role) > ancestors_role_priority
            ]

        return {
            "destroy": can_delete,
            "update": bool(set_role_to) and is_owner_or_admin,
            "partial_update": bool(set_role_to) and is_owner_or_admin,
            "retrieve": (self.user and self.user.id == user.id) or is_owner_or_admin,
            "set_role_to": set_role_to,
        }


class ItemInvitationQuerySet(AnnotateUserRoleQuerySetMixin, models.QuerySet):
    """Custom queryset for ItemInvitation model with additional methods."""

    path_property = "item__path"


class ItemInvitationManager(models.Manager.from_queryset(ItemInvitationQuerySet)):
    """Manager for ItemAccess model."""


class Invitation(BaseModel):
    """User invitation to an item."""

    email = models.EmailField(_("email address"), null=False, blank=False)
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.READER)
    issuer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="invitations",
        blank=True,
        null=True,
    )

    objects = ItemInvitationManager()

    class Meta:
        db_table = "drive_invitation"
        verbose_name = _("Item invitation")
        verbose_name_plural = _("Item invitations")
        constraints = [
            models.UniqueConstraint(
                fields=["email", "item"],
                name="email_and_item_unique_together",
            )
        ]

    def __str__(self):
        return f"{self.email} invited to {self.item}"

    def clean(self):
        """Validate fields."""
        super().clean()

        # Check if an identity already exists for the provided email
        if (
            User.objects.filter(email__iexact=self.email).exists()
            and not settings.OIDC_ALLOW_DUPLICATE_EMAILS
        ):
            raise ValidationError(
                {
                    "email": ValidationError(
                        "This email is already associated to a registered user.",
                        code="invitation_email_already_registered",
                    )
                }
            )

    @property
    def is_expired(self):
        """Calculate if invitation is still valid or has expired."""
        if not self.created_at:
            return None

        validity_duration = timedelta(seconds=settings.INVITATION_VALIDITY_DURATION)
        return timezone.now() > (self.created_at + validity_duration)

    def get_role(self, user):
        """Return the role a user has on an item related to this access.."""
        if not user.is_authenticated:
            return None

        try:
            roles = self.user_roles or []
        except AttributeError:
            roles = ItemAccess.objects.filter(
                models.Q(user=user) | models.Q(team__in=user.teams),
                item__path__ancestors=self.item.path,
            ).values_list("role", flat=True)

        return RoleChoices.max(*roles)

    def get_abilities(self, user):
        """Compute and return abilities for a given user."""
        user_role = self.get_role(user)
        is_owner_or_admin = user_role in PRIVILEGED_ROLES

        return {
            "destroy": is_owner_or_admin,
            "update": is_owner_or_admin,
            "partial_update": is_owner_or_admin,
            "retrieve": is_owner_or_admin,
        }
