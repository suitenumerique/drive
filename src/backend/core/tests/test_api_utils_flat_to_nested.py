"""Test the utils function flat_to_nested."""

import pytest

from core.api.utils import flat_to_nested


def test_flat_to_nested_with_ordered_list():
    """Test the function flat_to_nested."""

    flat_items_list = [
        {
            "depth": 1,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2",
            "title": "root",
            "created_at": "2021-01-01T00:00:00Z",
        },
        {
            "depth": 2,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af",
            "title": "level1_1",
            "created_at": "2021-01-01T12:00:00Z",
        },
        {
            "depth": 3,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "191d6a82-ece9-4a7e-8898-1453aef0e533"
            ),
            "title": "level2_1",
            "created_at": "2021-01-04T10:00:00Z",
        },
        {
            "depth": 3,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "f7ef4218-1d57-4cb0-847d-583e80a357d0"
            ),
            "title": "level2_2",
            "created_at": "2021-01-04T12:00:00Z",
        },
        {
            "depth": 4,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "f7ef4218-1d57-4cb0-847d-583e80a357d0.febc9574-f29a-44ad-810a-7e35ea19c62e"
            ),
            "title": "level3_1",
            "created_at": "2021-01-05T00:00:00Z",
        },
        {
            "depth": 2,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.1cfed79d-d3e6-4ee6-a334-b4a7a045213f",
            "title": "level1_2",
            "created_at": "2021-01-02T00:00:00Z",
        },
        {
            "depth": 2,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.1276b22f-9fa7-423a-89d1-457abfedb083",
            "title": "level1_3",
            "created_at": "2021-01-03T00:00:00Z",
        },
    ]

    assert flat_to_nested(flat_items_list) == {
        "depth": 1,
        "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2",
        "title": "root",
        "created_at": "2021-01-01T00:00:00Z",
        "children": [
            {
                "depth": 2,
                "path": (
                    "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                    "b3509308-b8f9-405e-936a-a320284917af"
                ),
                "title": "level1_1",
                "created_at": "2021-01-01T12:00:00Z",
                "children": [
                    {
                        "depth": 3,
                        "path": (
                            "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                            "b3509308-b8f9-405e-936a-a320284917af."
                            "191d6a82-ece9-4a7e-8898-1453aef0e533"
                        ),
                        "title": "level2_1",
                        "created_at": "2021-01-04T10:00:00Z",
                        "children": [],
                    },
                    {
                        "depth": 3,
                        "path": (
                            "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                            "b3509308-b8f9-405e-936a-a320284917af."
                            "f7ef4218-1d57-4cb0-847d-583e80a357d0"
                        ),
                        "title": "level2_2",
                        "created_at": "2021-01-04T12:00:00Z",
                        "children": [
                            {
                                "depth": 4,
                                "path": (
                                    "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                                    "b3509308-b8f9-405e-936a-a320284917af."
                                    "f7ef4218-1d57-4cb0-847d-583e80a357d0."
                                    "febc9574-f29a-44ad-810a-7e35ea19c62e"
                                ),
                                "title": "level3_1",
                                "created_at": "2021-01-05T00:00:00Z",
                                "children": [],
                            }
                        ],
                    },
                ],
            },
            {
                "depth": 2,
                "path": (
                    "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                    "1cfed79d-d3e6-4ee6-a334-b4a7a045213f"
                ),
                "title": "level1_2",
                "created_at": "2021-01-02T00:00:00Z",
                "children": [],
            },
            {
                "depth": 2,
                "path": (
                    "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                    "1276b22f-9fa7-423a-89d1-457abfedb083"
                ),
                "title": "level1_3",
                "created_at": "2021-01-03T00:00:00Z",
                "children": [],
            },
        ],
    }


def test_utils_flat_to_nested_with_not_ordered_list():
    """Test the function flat_to_nested."""

    flat_items_list = [
        {
            "depth": 2,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af",
            "title": "level1_1",
            "created_at": "2021-01-01T12:00:00Z",
        },
        {
            "depth": 3,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "191d6a82-ece9-4a7e-8898-1453aef0e533"
            ),
            "title": "level2_1",
            "created_at": "2021-01-04T10:00:00Z",
        },
        {
            "depth": 2,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.1cfed79d-d3e6-4ee6-a334-b4a7a045213f",
            "title": "level1_2",
            "created_at": "2021-01-02T00:00:00Z",
        },
        {
            "depth": 1,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2",
            "title": "root",
            "created_at": "2021-01-01T00:00:00Z",
        },
        {
            "depth": 2,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.1276b22f-9fa7-423a-89d1-457abfedb083",
            "title": "level1_3",
            "created_at": "2021-01-03T00:00:00Z",
        },
        {
            "depth": 3,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "f7ef4218-1d57-4cb0-847d-583e80a357d0"
            ),
            "title": "level2_2",
            "created_at": "2021-01-04T12:00:00Z",
        },
        {
            "depth": 4,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "f7ef4218-1d57-4cb0-847d-583e80a357d0.febc9574-f29a-44ad-810a-7e35ea19c62e"
            ),
            "title": "level3_1",
            "created_at": "2021-01-05T00:00:00Z",
        },
    ]

    assert flat_to_nested(flat_items_list) == {
        "depth": 1,
        "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2",
        "title": "root",
        "created_at": "2021-01-01T00:00:00Z",
        "children": [
            {
                "depth": 2,
                "path": (
                    "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                    "b3509308-b8f9-405e-936a-a320284917af"
                ),
                "title": "level1_1",
                "created_at": "2021-01-01T12:00:00Z",
                "children": [
                    {
                        "depth": 3,
                        "path": (
                            "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                            "b3509308-b8f9-405e-936a-a320284917af."
                            "191d6a82-ece9-4a7e-8898-1453aef0e533"
                        ),
                        "title": "level2_1",
                        "created_at": "2021-01-04T10:00:00Z",
                        "children": [],
                    },
                    {
                        "depth": 3,
                        "path": (
                            "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                            "b3509308-b8f9-405e-936a-a320284917af."
                            "f7ef4218-1d57-4cb0-847d-583e80a357d0"
                        ),
                        "title": "level2_2",
                        "created_at": "2021-01-04T12:00:00Z",
                        "children": [
                            {
                                "depth": 4,
                                "path": (
                                    "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                                    "b3509308-b8f9-405e-936a-a320284917af."
                                    "f7ef4218-1d57-4cb0-847d-583e80a357d0."
                                    "febc9574-f29a-44ad-810a-7e35ea19c62e"
                                ),
                                "title": "level3_1",
                                "created_at": "2021-01-05T00:00:00Z",
                                "children": [],
                            }
                        ],
                    },
                ],
            },
            {
                "depth": 2,
                "path": (
                    "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                    "1cfed79d-d3e6-4ee6-a334-b4a7a045213f"
                ),
                "title": "level1_2",
                "created_at": "2021-01-02T00:00:00Z",
                "children": [],
            },
            {
                "depth": 2,
                "path": (
                    "9bd75ab3-408e-443f-8d76-cd67550c38c2."
                    "1276b22f-9fa7-423a-89d1-457abfedb083"
                ),
                "title": "level1_3",
                "created_at": "2021-01-03T00:00:00Z",
                "children": [],
            },
        ],
    }


def test_utils_flat_to_nested_not_started_with_a_depth_1():
    """Test the function flat_to_nested."""

    flat_items_list = [
        {
            "depth": 2,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af",
            "title": "level1_1",
            "created_at": "2021-01-01T12:00:00Z",
        },
        {
            "depth": 3,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "191d6a82-ece9-4a7e-8898-1453aef0e533"
            ),
            "title": "level2_1",
            "created_at": "2021-01-04T10:00:00Z",
        },
        {
            "depth": 3,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "f7ef4218-1d57-4cb0-847d-583e80a357d0"
            ),
            "title": "level2_2",
            "created_at": "2021-01-04T12:00:00Z",
        },
    ]

    assert flat_to_nested(flat_items_list) == {
        "depth": 2,
        "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af",
        "title": "level1_1",
        "created_at": "2021-01-01T12:00:00Z",
        "children": [
            {
                "depth": 3,
                "path": (
                    "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                    "191d6a82-ece9-4a7e-8898-1453aef0e533"
                ),
                "title": "level2_1",
                "children": [],
                "created_at": "2021-01-04T10:00:00Z",
            },
            {
                "depth": 3,
                "path": (
                    "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                    "f7ef4218-1d57-4cb0-847d-583e80a357d0"
                ),
                "title": "level2_2",
                "children": [],
                "created_at": "2021-01-04T12:00:00Z",
            },
        ],
    }


def test_utils_flat_to_nested_with_two_root_elements():
    """
    Test the function flat_to_nested with multiple root elements. Should raise a ValueError
    if it's the case.
    """

    flat_items_list = [
        {
            "depth": 1,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2",
            "title": "root",
            "created_at": "2021-01-01T00:00:00Z",
        },
        {
            "depth": 1,
            "path": "b0c743a5-5fd5-490a-8ef8-f996ddf707d4",
            "title": "root2",
            "created_at": "2021-02-01T00:00:00Z",
        },
        {
            "depth": 2,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af",
            "title": "level1_1",
            "created_at": "2021-01-01T12:00:00Z",
        },
        {
            "depth": 3,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "191d6a82-ece9-4a7e-8898-1453aef0e533"
            ),
            "title": "level2_1",
            "created_at": "2021-01-04T10:00:00Z",
        },
        {
            "depth": 3,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "f7ef4218-1d57-4cb0-847d-583e80a357d0"
            ),
            "title": "level2_2",
            "created_at": "2021-01-04T12:00:00Z",
        },
        {
            "depth": 4,
            "path": (
                "9bd75ab3-408e-443f-8d76-cd67550c38c2.b3509308-b8f9-405e-936a-a320284917af."
                "f7ef4218-1d57-4cb0-847d-583e80a357d0.febc9574-f29a-44ad-810a-7e35ea19c62e"
            ),
            "title": "level3_1",
            "created_at": "2021-01-05T00:00:00Z",
        },
        {
            "depth": 2,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.1cfed79d-d3e6-4ee6-a334-b4a7a045213f",
            "title": "level1_2",
            "created_at": "2021-01-02T00:00:00Z",
        },
        {
            "depth": 2,
            "path": "9bd75ab3-408e-443f-8d76-cd67550c38c2.1276b22f-9fa7-423a-89d1-457abfedb083",
            "title": "level1_3",
            "created_at": "2021-01-03T00:00:00Z",
        },
    ]

    with pytest.raises(ValueError):
        flat_to_nested(flat_items_list)


def test_utils_flat_to_nested_with_empty_list():
    """Test the function flat_to_nested with an empty list. Should return an empty dict."""

    # pylint: disable=use-implicit-booleaness-not-comparison
    assert flat_to_nested([]) == {}
