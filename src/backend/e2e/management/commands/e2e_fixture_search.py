"""E2E fixture search."""

from django.core.management.base import BaseCommand

from core import factories, models

from e2e.utils import get_or_create_e2e_user


class Command(BaseCommand):
    """E2E fixture search."""

    help = "Generates E2E search fixtures."

    def handle(self, *args, **options):
        """E2E fixture search."""
        user = get_or_create_e2e_user("drive@example.com")
        content = [
            {
                "title": "Project 2025",
                "type": models.ItemTypeChoices.FOLDER,
                "creator": user,
                "children": [
                    {
                        "title": "Budget report",
                        "type": models.ItemTypeChoices.FILE,
                        "creator": user,
                    },
                    {
                        "title": "Sales report",
                        "type": models.ItemTypeChoices.FILE,
                        "creator": user,
                    },
                ],
            },
            {
                "title": "Dev Team",
                "type": models.ItemTypeChoices.FOLDER,
                "creator": user,
                "children": [
                    {
                        "title": "Backlog",
                        "type": models.ItemTypeChoices.FILE,
                        "creator": user,
                    },
                    {
                        "title": "Meetings",
                        "type": models.ItemTypeChoices.FOLDER,
                        "creator": user,
                        "children": [
                            {
                                "title": "Meeting notes 5th September",
                                "type": models.ItemTypeChoices.FILE,
                                "creator": user,
                            },
                            {
                                "title": "Meeting notes 15th September",
                                "type": models.ItemTypeChoices.FILE,
                                "creator": user,
                            },
                        ],
                    },
                ],
            },
        ]

        for data in content:
            item = factories.ItemFactory(
                title=data["title"], type=data["type"], creator=data["creator"]
            )
            factories.UserItemAccessFactory(
                item=item, user=user, role=models.RoleChoices.OWNER
            )
            if "children" in data:
                for child_data in data["children"]:
                    self._create_item(item, child_data, user)

    def _create_item(self, parent, data, user):
        item = factories.ItemFactory(
            title=data["title"],
            type=data["type"],
            creator=data["creator"],
            parent=parent,
        )
        if "children" in data:
            for child_data in data["children"]:
                self._create_item(item, child_data, user)
