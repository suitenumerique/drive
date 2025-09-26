"""Test utils.is_previewable_item"""

import pytest

from core import factories, models
from core.api import utils

pytestmark = pytest.mark.django_db


def test_is_previewable_item_returns_false_when_mimetype_is_none():
    """Test is_previewable_item returns False when mimetype is None"""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="file.bin",
        mimetype=None,
    )

    assert utils.is_previewable_item(item) is False


def test_is_previewable_item_returns_true_for_prefix_allowed_type_image_png():
    """Test is_previewable_item returns True for prefix allowed type image/png"""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="image.png",
        mimetype="image/png",
    )

    assert utils.is_previewable_item(item) is True


def test_is_previewable_item_returns_true_for_exact_allowed_type_pdf():
    """Test is_previewable_item returns True for exact allowed type application/pdf"""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="document.pdf",
        mimetype="application/pdf",
    )

    assert utils.is_previewable_item(item) is True


def test_is_previewable_item_returns_false_for_unallowed_type_json():
    """Test is_previewable_item returns False for unallowed type application/json"""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="data.json",
        mimetype="application/json",
    )

    assert utils.is_previewable_item(item) is False


def test_is_previewable_item_returns_false_for_exact_mismatch_pdfx():
    """Test is_previewable_item returns False for exact mismatch application/pdfx"""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="document.pdfx",
        mimetype="application/pdfx",
    )

    assert utils.is_previewable_item(item) is False
