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
                    {
                        "title": "I am deleted",
                        "type": models.ItemTypeChoices.FOLDER,
                        "creator": user,
                        "deleted": True,
                    },
                    {
                        "title": "Resume",
                        "type": models.ItemTypeChoices.FILE,
                        "creator": user,
                        "deleted": True,
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

        self._create_item(None, content)

    def _create_item(self, parent, content, depth=0):
        if content is None:
            return
        for data in content:
            item = factories.ItemFactory(
                title=data["title"],
                type=data["type"],
                creator=data["creator"],
                parent=parent,
                users=[(data["creator"], models.RoleChoices.OWNER)]
                if depth == 0
                else None,
            )
            if data.get("deleted"):
                item.soft_delete()
            self.stdout.write(
                f"Item created: {item.title} with parent: {parent.title if parent else None} "
                f"and depth: {depth} and deleted: {data.get('deleted')}"
            )
            self._create_item(item, data.get("children"), depth + 1)
