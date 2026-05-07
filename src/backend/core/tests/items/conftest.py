"""Shared fixtures for items API tests."""

from django.core.cache import cache

import pytest

from core import factories, models
from wopi.tasks.configure_wopi import WOPI_CONFIGURATION_CACHE_KEY

WOPI_DOC_ODT_PNG_EXPECTED_ACTIONS = {
    "legacy.doc": ["convert", "edit"],
    "modern.odt": ["edit"],
    "image.png": [],
}


@pytest.fixture(name="wopi_doc_odt_cache")
def fixture_wopi_doc_odt_cache():
    """Populate the WOPI configuration cache with `doc` and `odt` extensions."""
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {},
            "extensions": {
                "doc": {
                    "edit": {"url": "https://collabora.example/edit", "client": "collabora"},
                    "convert": {
                        "url": "https://onlyoffice.example/convert",
                        "client": "onlyoffice",
                    },
                },
                "odt": {
                    "edit": {"url": "https://collabora.example/edit", "client": "collabora"},
                },
            },
        },
    )


def make_doc_odt_png_files(user, parent=None):
    """Create a .doc, an .odt and a .png file owned by `user`."""
    for filename, mimetype in [
        ("legacy.doc", "application/msword"),
        ("modern.odt", "application/vnd.oasis.opendocument.text"),
        ("image.png", "image/png"),
    ]:
        item = factories.ItemFactory(
            parent=parent,
            type=models.ItemTypeChoices.FILE,
            filename=filename,
            mimetype=mimetype,
            update_upload_state=models.ItemUploadStateChoices.READY,
        )
        factories.UserItemAccessFactory(item=item, user=user, role="owner")
