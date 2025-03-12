# ruff: noqa: S311
"""
Core application factories
"""

from django.conf import settings
from django.contrib.auth.hashers import make_password

import factory.fuzzy
from faker import Faker

from core import models

fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    """A factory to random users for testing purposes."""

    class Meta:
        model = models.User
        skip_postgeneration_save = True

    sub = factory.Sequence(lambda n: f"user{n!s}")
    email = factory.Faker("email")
    full_name = factory.Faker("name")
    short_name = factory.Faker("first_name")
    language = factory.fuzzy.FuzzyChoice([lang[0] for lang in settings.LANGUAGES])
    password = make_password("password")


class ParentNodeFactory(factory.declarations.ParameteredAttribute):
    """Custom factory attribute for setting the parent node."""

    def generate(self, step, params):
        """
        Generate a parent node for the factory.

        This method is invoked during the factory's build process to determine the parent
        node of the current object being created. If `params` is provided, it uses the factory's
        metadata to recursively create or fetch the parent node. Otherwise, it returns `None`.
        """
        if not params:
            return None
        subfactory = step.builder.factory_meta.factory
        return step.recurse(subfactory, params)


class ItemFactory(factory.django.DjangoModelFactory):
    """A factory to create items"""

    class Meta:
        model = models.Item
        django_get_or_create = ("title",)
        skip_postgeneration_save = True

    # parent = ParentNodeFactory()

    title = factory.Sequence(lambda n: f"item{n}")
    creator = factory.SubFactory(UserFactory)
    deleted_at = None
    link_reach = factory.fuzzy.FuzzyChoice(
        [a[0] for a in models.LinkReachChoices.choices]
    )
    link_role = factory.fuzzy.FuzzyChoice(
        [r[0] for r in models.LinkRoleChoices.choices]
    )
    type = factory.fuzzy.FuzzyChoice([t[0] for t in models.ItemTypeChoices.choices])
    filename = factory.lazy_attribute(
        lambda o: factory.Faker("file_name")
        if o.type == models.ItemTypeChoices.FILE
        else None
    )

    # @classmethod
    # def _create(cls, model_class, *args, **kwargs):
    #     """
    #     Custom creation logic for the factory: creates an item as a child node if
    #     a parent is provided; otherwise, creates it as a root node.
    #     """
    #     parent = kwargs.pop("parent", None)

    #     if parent:
    #         # Add as a child node
    #         kwargs["ancestors_deleted_at"] = (
    #             kwargs.get("ancestors_deleted_at") or parent.ancestors_deleted_at
    #         )
    #         return parent.add_child(**kwargs)

    #     # Add as a root node
    #     return model_class.add_root(**kwargs)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.objects.create_child(**kwargs)

    @factory.lazy_attribute
    def ancestors_deleted_at(self):
        """Should always be set when "deleted_at" is set."""
        return self.deleted_at

    @factory.post_generation
    def users(self, create, extracted, **kwargs):
        """Add users to item from a given list of users with or without roles."""
        if create and extracted:
            for item in extracted:
                if isinstance(item, models.User):
                    UserItemAccessFactory(item=self, user=item)
                else:
                    UserItemAccessFactory(item=self, user=item[0], role=item[1])

    @factory.post_generation
    def teams(self, create, extracted, **kwargs):
        """Add teams to item from a given list of teams with or without roles."""
        if create and extracted:
            for item in extracted:
                if isinstance(item, str):
                    TeamItemAccessFactory(item=self, team=item)
                else:
                    TeamItemAccessFactory(item=self, team=item[0], role=item[1])

    @factory.post_generation
    def link_traces(self, create, extracted, **kwargs):
        """Add link traces to item from a given list of users."""
        if create and extracted:
            for item in extracted:
                models.LinkTrace.objects.create(item=self, user=item)

    @factory.post_generation
    def favorited_by(self, create, extracted, **kwargs):
        """Mark item as favorited by a list of users."""
        if create and extracted:
            for item in extracted:
                models.ItemFavorite.objects.create(item=self, user=item)


class UserItemAccessFactory(factory.django.DjangoModelFactory):
    """Create fake item user accesses for testing."""

    class Meta:
        model = models.ItemAccess

    item = factory.SubFactory(ItemFactory)
    user = factory.SubFactory(UserFactory)
    role = factory.fuzzy.FuzzyChoice([r[0] for r in models.RoleChoices.choices])


class TeamItemAccessFactory(factory.django.DjangoModelFactory):
    """Create fake item team accesses for testing."""

    class Meta:
        model = models.ItemAccess

    item = factory.SubFactory(ItemFactory)
    team = factory.Sequence(lambda n: f"team{n}")
    role = factory.fuzzy.FuzzyChoice([r[0] for r in models.RoleChoices.choices])


class InvitationFactory(factory.django.DjangoModelFactory):
    """A factory to create invitations for a user"""

    class Meta:
        model = models.Invitation

    email = factory.Faker("email")
    item = factory.SubFactory(ItemFactory)
    role = factory.fuzzy.FuzzyChoice([role[0] for role in models.RoleChoices.choices])
    issuer = factory.SubFactory(UserFactory)
