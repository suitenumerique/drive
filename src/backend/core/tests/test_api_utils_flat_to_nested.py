"""Test the utils function flat_to_nested."""

import pytest

from core.api.utils import flat_to_nested


def test_flat_to_nested_with_ordered_list():
    """Test the function flat_to_nested."""

    flat_items_list = [
        {"depth": 1, "path": "0000000", "title": "root"},
        {"depth": 2, "path": "0000000.0000000", "title": "level1_1"},
        {"depth": 3, "path": "0000000.0000000.0000003", "title": "level2_1"},
        {"depth": 3, "path": "0000000.0000000.0000004", "title": "level2_2"},
        {"depth": 4, "path": "0000000.0000000.0000004.0000004", "title": "level3_1"},
        {"depth": 2, "path": "0000000.0000001", "title": "level1_2"},
        {"depth": 2, "path": "0000000.0000002", "title": "level1_3"},
    ]

    assert flat_to_nested(flat_items_list) == {
        "depth": 1,
        "path": "0000000",
        "title": "root",
        "children": [
            {
                "depth": 2,
                "path": "0000000.0000000",
                "title": "level1_1",
                "children": [
                    {
                        "depth": 3,
                        "path": "0000000.0000000.0000003",
                        "title": "level2_1",
                        "children": [],
                    },
                    {
                        "depth": 3,
                        "path": "0000000.0000000.0000004",
                        "title": "level2_2",
                        "children": [
                            {
                                "depth": 4,
                                "path": "0000000.0000000.0000004.0000004",
                                "title": "level3_1",
                                "children": [],
                            }
                        ],
                    },
                ],
            },
            {
                "depth": 2,
                "path": "0000000.0000001",
                "title": "level1_2",
                "children": [],
            },
            {
                "depth": 2,
                "path": "0000000.0000002",
                "title": "level1_3",
                "children": [],
            },
        ],
    }


def test_utils_flat_to_nested_with_not_ordered_list():
    """Test the function flat_to_nested."""

    flat_items_list = [
        {"depth": 2, "path": "0000000.0000000", "title": "level1_1"},
        {"depth": 3, "path": "0000000.0000000.0000003", "title": "level2_1"},
        {"depth": 2, "path": "0000000.0000001", "title": "level1_2"},
        {"depth": 1, "path": "0000000", "title": "root"},
        {"depth": 2, "path": "0000000.0000002", "title": "level1_3"},
        {"depth": 3, "path": "0000000.0000000.0000004", "title": "level2_2"},
        {"depth": 4, "path": "0000000.0000000.0000004.0000004", "title": "level3_1"},
    ]

    assert flat_to_nested(flat_items_list) == {
        "depth": 1,
        "path": "0000000",
        "title": "root",
        "children": [
            {
                "depth": 2,
                "path": "0000000.0000000",
                "title": "level1_1",
                "children": [
                    {
                        "depth": 3,
                        "path": "0000000.0000000.0000003",
                        "title": "level2_1",
                        "children": [],
                    },
                    {
                        "depth": 3,
                        "path": "0000000.0000000.0000004",
                        "title": "level2_2",
                        "children": [
                            {
                                "depth": 4,
                                "path": "0000000.0000000.0000004.0000004",
                                "title": "level3_1",
                                "children": [],
                            }
                        ],
                    },
                ],
            },
            {
                "depth": 2,
                "path": "0000000.0000001",
                "title": "level1_2",
                "children": [],
            },
            {
                "depth": 2,
                "path": "0000000.0000002",
                "title": "level1_3",
                "children": [],
            },
        ],
    }


def test_utils_flat_to_nested_not_started_with_a_depth_1():
    """Test the function flat_to_nested."""

    flat_items_list = [
        {"depth": 2, "path": "0000000.0000000", "title": "level1_1"},
        {"depth": 3, "path": "0000000.0000000.0000000", "title": "level2_1"},
        {"depth": 3, "path": "0000000.0000000.0000001", "title": "level2_2"},
    ]

    assert flat_to_nested(flat_items_list) == {
        "depth": 2,
        "path": "0000000.0000000",
        "title": "level1_1",
        "children": [
            {
                "depth": 3,
                "path": "0000000.0000000.0000000",
                "title": "level2_1",
                "children": [],
            },
            {
                "depth": 3,
                "path": "0000000.0000000.0000001",
                "title": "level2_2",
                "children": [],
            },
        ],
    }


def test_utils_flat_to_nested_with_two_root_elements():
    """Test the function flat_to_nested with multiple root elements. Should raise a ValueError if it's the case."""

    flat_items_list = [
        {"depth": 1, "path": "0000000", "title": "root1"},
        {"depth": 1, "path": "0000001", "title": "root2"},
        {"depth": 2, "path": "0000000.0000000", "title": "level1_1"},
        {"depth": 3, "path": "0000000.0000000.0000000", "title": "level2_1"},
        {"depth": 3, "path": "0000000.0000000.0000001", "title": "level2_2"},
        {"depth": 2, "path": "0000001.0000001", "title": "level1_2"},
        {"depth": 3, "path": "0000001.0000001.0000001", "title": "level2_3"},
        {"depth": 3, "path": "0000001.0000001.0000002", "title": "level2_4"},
    ]

    with pytest.raises(ValueError):
        flat_to_nested(flat_items_list)


def test_utils_flat_to_nested_with_empty_list():
    """Test the function flat_to_nested with an empty list. Should return None."""

    assert flat_to_nested([]) == {}
