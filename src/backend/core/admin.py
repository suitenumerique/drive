"""Admin classes and registrations for core app."""

from functools import partial

from django.contrib import admin, messages
from django.contrib.auth import admin as auth_admin
from django.db import transaction
from django.db.models import Exists, OuterRef, Subquery, UUIDField
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast
from django.shortcuts import redirect
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _

from lasuite.malware_detection import malware_detection
from lasuite.malware_detection.admin import MalwareDetectionAdmin as BaseMalwareDetectionAdmin
from lasuite.malware_detection.models import MalwareDetection

from core import models
from core.tasks.user_reconciliation import user_reconciliation_csv_import_job


@admin.register(models.User)
class UserAdmin(auth_admin.UserAdmin):
    """Admin class for the User model"""

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "admin_email",
                    "password",
                )
            },
        ),
        (
            _("Personal info"),
            {
                "fields": (
                    "sub",
                    "email",
                    "full_name",
                    "short_name",
                    "language",
                    "timezone",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_device",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Entitlements"), {"fields": ("storage_limit_override",)}),
        (_("Important dates"), {"fields": ("created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    list_display = (
        "id",
        "sub",
        "full_name",
        "admin_email",
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "is_device",
        "storage_limit_override",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_staff", "is_superuser", "is_device", "is_active")
    ordering = (
        "is_active",
        "-is_superuser",
        "-is_staff",
        "-is_device",
        "-updated_at",
        "full_name",
    )
    readonly_fields = (
        "id",
        "sub",
        "email",
        "full_name",
        "short_name",
        "created_at",
        "updated_at",
    )
    search_fields = ("id", "sub", "admin_email", "email", "full_name")


@admin.register(models.UserReconciliationCsvImport)
class UserReconciliationCsvImportAdmin(admin.ModelAdmin):
    """Admin class for UserReconciliationCsvImport model."""

    list_display = ("id", "__str__", "created_at", "status")

    def save_model(self, request, obj, form, change):
        """Override save_model to trigger the import task on creation."""
        super().save_model(request, obj, form, change)

        if not change:
            # Defer to commit so the task does not run before the row is visible.
            transaction.on_commit(partial(user_reconciliation_csv_import_job.delay, obj.pk))
            messages.success(request, _("Import job created and queued."))
        return redirect("..")


@admin.action(description=_("Process selected user reconciliations"))
def process_reconciliation(_modeladmin, _request, queryset):
    """
    Admin action to process selected user reconciliations.
    The action will process only entries that are ready and have both emails checked.
    """
    processable_entries = queryset.filter(
        status="ready", active_email_checked=True, inactive_email_checked=True
    )

    for entry in processable_entries:
        entry.process_reconciliation_request()


@admin.register(models.UserReconciliation)
class UserReconciliationAdmin(admin.ModelAdmin):
    """Admin class for UserReconciliation model."""

    list_display = ["id", "__str__", "created_at", "status"]
    actions = [process_reconciliation]


class ItemAccessInline(admin.TabularInline):
    """Inline admin class for item accesses."""

    autocomplete_fields = ["user"]
    model = models.ItemAccess
    extra = 0


@admin.register(models.Item)
class ItemAdmin(admin.ModelAdmin):
    """item admin interface declaration."""

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "title",
                    "filename",
                    "size_display",
                    "deleted_at",
                    "ancestors_deleted_at",
                    "malware_detection_info",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "creator",
                    "link_reach",
                    "link_role",
                )
            },
        ),
        (
            _("Malware detection"),
            {"fields": ("upload_state",)},
        ),
        (
            _("Tree structure"),
            {
                "fields": (
                    "path",
                    "depth",
                    "numchild",
                )
            },
        ),
    )
    inlines = (ItemAccessInline,)
    list_display = (
        "id",
        "title",
        "type",
        "link_reach",
        "link_role",
        "upload_state",
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "creator",
        "depth",
        "id",
        "numchild",
        "path",
        "filename",
        "size_display",
        "deleted_at",
        "ancestors_deleted_at",
        "malware_detection_info",
    )
    search_fields = ("id", "title", "creator__email")
    list_filter = ("upload_state", "link_reach", "link_role")
    show_facets = admin.ShowFacets.ALWAYS
    actions = (
        "trigger_file_analysis",
        "mark_items_ready",
        "mark_items_file_too_large",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate_with_numchild()

        return queryset

    @admin.display(description=_("size"))
    def size_display(self, obj):
        """Return the human readable size of the item file."""
        if obj.size is None:
            return None
        return filesizeformat(obj.size)

    def trigger_file_analysis(self, request, queryset):
        """Reanalyse the file of the items."""

        for item in queryset:
            if item.type == models.ItemTypeChoices.FILE:
                malware_detection.analyse_file(item.file_key, item_id=item.id)

        self.message_user(request, "The files have been scheduled for a new analysis.")

    def _force_upload_state(self, request, queryset, upload_state):
        """Force the upload state of the selected file items and drop their detections."""
        items = queryset.filter(type=models.ItemTypeChoices.FILE)
        paths = [item.file_key for item in items]
        deleted, _details = MalwareDetection.objects.filter(path__in=paths).delete()
        updated = items.update(upload_state=upload_state)
        self.message_user(
            request,
            f"{updated} items marked as {upload_state}, {deleted} detections deleted.",
        )

    @admin.action(description=_("Mark items as ready"))
    def mark_items_ready(self, request, queryset):
        """Force selected file items to the ready state."""
        self._force_upload_state(request, queryset, models.ItemUploadStateChoices.READY)

    @admin.action(description=_("Mark items as too large to analyze"))
    def mark_items_file_too_large(self, request, queryset):
        """Force selected file items to the too large to analyze state."""
        self._force_upload_state(
            request, queryset, models.ItemUploadStateChoices.FILE_TOO_LARGE_TO_ANALYZE
        )


@admin.register(models.Invitation)
class InvitationAdmin(admin.ModelAdmin):
    """Admin interface to handle invitations."""

    fields = (
        "email",
        "item",
        "role",
        "created_at",
        "issuer",
    )
    readonly_fields = (
        "created_at",
        "is_expired",
        "issuer",
    )
    list_display = (
        "email",
        "item",
        "created_at",
        "is_expired",
    )

    def save_model(self, request, obj, form, change):
        obj.issuer = request.user
        obj.save()


class ItemExistsFilter(admin.SimpleListFilter):
    """Filter malware detection records on the existence of their related item."""

    title = _("item exists")
    parameter_name = "item_exists"

    def lookups(self, request, model_admin):
        """Return the filter options."""
        return [("yes", _("Yes")), ("no", _("No"))]

    def queryset(self, request, queryset):
        """Filter the queryset on the item_exists annotation."""
        if self.value() == "yes":
            return queryset.filter(item_exists=True)
        if self.value() == "no":
            return queryset.filter(item_exists=False)
        return queryset


admin.site.unregister(MalwareDetection)


@admin.register(MalwareDetection)
class MalwareDetectionAdmin(BaseMalwareDetectionAdmin):
    """Admin class for the MalwareDetection model with item existence tooling."""

    list_display = BaseMalwareDetectionAdmin.list_display + ("item_exists", "item_size")
    list_filter = BaseMalwareDetectionAdmin.list_filter + (ItemExistsFilter,)
    actions = BaseMalwareDetectionAdmin.actions + (
        "abandon_analysis_mark_item_ready",
        "abandon_analysis_mark_item_file_too_large",
    )

    def _abandon_analyses(self, request, queryset, upload_state):
        """Delete the selected detections and force the upload state of their items."""
        item_ids = [
            item_id for item_id in queryset.values_list("parameters__item_id", flat=True) if item_id
        ]
        updated = models.Item.objects.filter(id__in=item_ids).update(upload_state=upload_state)
        deleted, _details = queryset.delete()
        self.message_user(
            request,
            f"{deleted} detections deleted, {updated} items marked as {upload_state}.",
        )

    @admin.action(description=_("Abandon analysis and mark item as ready"))
    def abandon_analysis_mark_item_ready(self, request, queryset):
        """Delete selected detections and mark their items as ready."""
        self._abandon_analyses(request, queryset, models.ItemUploadStateChoices.READY)

    @admin.action(description=_("Abandon analysis and mark item as too large to analyze"))
    def abandon_analysis_mark_item_file_too_large(self, request, queryset):
        """Delete selected detections and mark their items as too large to analyze."""
        self._abandon_analyses(
            request, queryset, models.ItemUploadStateChoices.FILE_TOO_LARGE_TO_ANALYZE
        )

    def get_queryset(self, request):
        """Annotate records with the existence and size of their related item."""
        related_items = models.Item.objects.filter(
            id=Cast(
                KeyTextTransform("item_id", OuterRef("parameters")),
                output_field=UUIDField(),
            )
        )
        return (
            super()
            .get_queryset(request)
            .annotate(
                item_exists=Exists(related_items),
                item_size=Subquery(related_items.values("size")[:1]),
            )
        )

    @admin.display(boolean=True, description=_("item exists"))
    def item_exists(self, obj):
        """Return whether the item of the record still exists."""
        return obj.item_exists

    @admin.display(description=_("item size"), ordering="item_size")
    def item_size(self, obj):
        """Return the human readable size of the item file."""
        if obj.item_size is None:
            return None
        return filesizeformat(obj.item_size)
