"""Test for the sanitize_filename function in the api utils module."""

from django.core.exceptions import ValidationError

import pytest

from core.api.utils import sanitize_filename


@pytest.mark.parametrize(
    "filename,expected_filename",
    [
        # no change,
        ("hello.txt", "hello.txt"),
        # XSS / HTML injection
        ("><img src=x onerror=alert()>␊.txt", "img_srcx_onerroralert.txt"),
        # Path traversal
        ("../../etc/passwd.txt", "....etcpasswd.txt"),  # every / are renmoved
        # Null bytes
        ("file\x00name.txt", "filename.txt"),
        # Unicode / homoglyph
        ("filеname.txt", "filname.txt"),  # Cyrillic 'е'
        # remove white spaces
        ("my file name.txt", "my_file_name.txt"),
        # accent are removed
        ("héllo.txt", "hello.txt"),
        ("wörld.txt", "world.txt"),
        ("café résumé.txt", "cafe_resume.txt"),
        # special characters are removed
        ("my*file?.doc", "myfile.doc"),
        # strip whitespaces
        (" my_file.txt ", "my_file.txt"),
        ("my_file.txt ", "my_file.txt"),
        (" my_file.txt", "my_file.txt"),
    ],
)
def test_api_utils_sanitize_filename(filename, expected_filename):
    """test filename sanitize function."""

    assert sanitize_filename(filename) == expected_filename


@pytest.mark.parametrize("illegal_char", ["\\", "/", ":", "*", "?", '"', "<", ">", "|"])
def test_api_utils_sanitize_filename_illegal_chars_replaced(illegal_char):
    """remove illegal chars"""
    result = sanitize_filename(f"my{illegal_char}file.txt")
    assert illegal_char not in result
    assert result == "myfile.txt"


@pytest.mark.parametrize("filename", ["!@#$%^&*().txt", "   .md", "  "])
def test_api_utils_sanitize_filename_resulting_in_empty_name_raise_an_exception(
    filename,
):
    """Test filename empyt once sanitize should raise an exception"""

    with pytest.raises(ValidationError):
        sanitize_filename(filename)
