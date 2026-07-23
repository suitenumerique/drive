"""Service for sharing items with registered users and inviting contacts."""

from django.db import models as db
from django.db import transaction
from django.db.models.functions import Lower

from core import models


def batch_share_process_rows(item, issuer, rows):
    """
    Create the accesses and invitations for the given {email: role} mapping.

    Emails matching an existing user get an access unless they already hold an
    equal or higher role on the item or one of its ancestors, other emails get
    an invitation unless one already exists. Return the created shares and the
    skipped emails.
    """
    users_by_email = {}
    users_queryset = models.User.objects.annotate(email_lower=Lower("email")).filter(
        email_lower__in=rows.keys()
    )
    for user in users_queryset:
        users_by_email.setdefault(user.email.lower(), user)

    # Compute the max role each matched user already holds on the item or one
    # of its ancestors, mirroring the single access creation checks. Users with
    # an explicit access on the item itself are always skipped as the access is
    # unique per user and item.
    ancestor_qs = (item.ancestors() | models.Item.objects.filter(pk=item.pk)).filter(
        ancestors_deleted_at__isnull=True
    )
    max_role_by_user_id = {}
    users_with_explicit_access = set()
    existing_accesses = models.ItemAccess.objects.filter(
        item__in=ancestor_qs, user__in=users_by_email.values()
    ).values_list("user_id", "item_id", "role")
    for user_id, item_id, role in existing_accesses:
        max_role_by_user_id[user_id] = models.RoleChoices.max(
            max_role_by_user_id.get(user_id), role
        )
        if item_id == item.pk:
            users_with_explicit_access.add(user_id)

    already_invited = set(
        item.invitations.filter(email__in=rows.keys()).values_list("email", flat=True)
    )

    skipped = []
    created_accesses = []
    created_invitations = []
    with transaction.atomic():
        for email, role in rows.items():
            if user := users_by_email.get(email):
                max_ancestors_role = max_role_by_user_id.get(user.id)
                if user.id in users_with_explicit_access or models.RoleChoices.get_priority(
                    max_ancestors_role
                ) >= models.RoleChoices.get_priority(role):
                    skipped.append({"email": email, "reason": "already_shared"})
                    continue
                access = models.ItemAccess.objects.create(item=item, user=user, role=role)
                synchronize_descendants_accesses(item, access)
                created_accesses.append((email, role))
            elif email in already_invited:
                skipped.append({"email": email, "reason": "already_invited"})
            else:
                models.Invitation.objects.create(item=item, email=email, role=role, issuer=issuer)
                created_invitations.append((email, role))

    return created_accesses, created_invitations, skipped


def synchronize_descendants_accesses(item, access):
    """
    Syncronize the accesses of the descendants of the item
    by removing accesses with roles lower than the current user's role.
    """
    descendants = item.descendants().filter(ancestors_deleted_at__isnull=True)

    condition_filter = db.Q()
    if access.user:
        condition_filter |= db.Q(user=access.user)
    if access.team:
        condition_filter |= db.Q(team=access.team)

    role_priority = models.RoleChoices.get_priority(access.role)

    lower_roles = [
        role
        for role in models.RoleChoices.values
        if models.RoleChoices.get_priority(role) <= role_priority
    ]

    models.ItemAccess.objects.filter(
        condition_filter, item__in=descendants, role__in=lower_roles
    ).delete()
