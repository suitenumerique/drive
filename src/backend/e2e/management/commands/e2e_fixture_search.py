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
        other = factories.UserFactory()
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
                        "filename": "budget-report.pdf",
                    },
                    {
                        "title": "Sales report",
                        "type": models.ItemTypeChoices.FILE,
                        "creator": user,
                        "filename": "sales-report.pdf",
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
                        "filename": "resume.pdf",
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
                        "filename": "backlog.pdf",
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
                                "filename": "meeting-notes-5th-september.pdf",
                            },
                            {
                                "title": "Meeting notes 15th September",
                                "type": models.ItemTypeChoices.FILE,
                                "creator": user,
                                "filename": "meeting-notes-15th-september.pdf",
                            },
                        ],
                    },
                ],
            },
            {
                "title": "Quarterly review mine",
                "type": models.ItemTypeChoices.FILE,
                "creator": user,
                "filename": "quarterly-mine.pdf",
            },
            {
                "title": "Quarterly review starred",
                "type": models.ItemTypeChoices.FILE,
                "creator": user,
                "filename": "quarterly-starred.pdf",
                "favorite": True,
            },
            {
                "title": "Quarterly review shared",
                "type": models.ItemTypeChoices.FILE,
                "creator": other,
                "filename": "quarterly-shared.pdf",
                "access": [(user, models.RoleChoices.READER)],
            },
        ]

        self._create_item(None, content, favorite_user=user)

    def _create_item(self, parent, content, depth=0, favorite_user=None):
        if content is None:
            return
        for data in content:
            item = factories.ItemFactory(
                title=data["title"],
                type=data["type"],
                creator=data["creator"],
                parent=parent,
                filename=data.get("filename"),
                update_upload_state=models.ItemUploadStateChoices.READY
                if data["type"] == models.ItemTypeChoices.FILE
                else None,
                users=[(data["creator"], models.RoleChoices.OWNER)] if depth == 0 else None,
            )
            if data.get("deleted"):
                item.soft_delete()
            for access_user, role in data.get("access", []):
                factories.UserItemAccessFactory(item=item, user=access_user, role=role)
            if data.get("favorite") and favorite_user:
                models.ItemFavorite.objects.create(user=favorite_user, item=item)
            self.stdout.write(
                f"Item created: {item.title} with parent: {parent.title if parent else None} "
                f"and depth: {depth} and deleted: {data.get('deleted')}"
            )
            self._create_item(item, data.get("children"), depth + 1, favorite_user)
