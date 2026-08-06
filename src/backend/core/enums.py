"""
Core application enums declaration
"""

from django.conf import global_settings
from django.utils.translation import gettext_lazy as _

# In Django's code base, `LANGUAGES` is set by default with all supported languages.
# We can use it for the choice of languages which should not be limited to the few languages
# active in the app.
# pylint: disable=no-member
ALL_LANGUAGES = {language: _(name) for language, name in global_settings.LANGUAGES}

# Mapping of the extensions accepted for file creation from a template to
# the template file shipped in assets/file_templates.
TEMPLATE_FILES = {
    "odt": "template.odt",
    "ods": "template.ods",
    "odp": "template.odp",
}

# Mapping of file type categories to the filename extensions they group together.
# Used to filter items by file type, the "other" category matching any unlisted extension.
FILE_CATEGORY_EXTENSIONS = {
    "doc": ["doc", "docx", "odt", "txt", "rtf", "md", "pages"],
    "powerpoint": ["ppt", "pptx", "odp", "key"],
    "calc": ["xls", "xlsx", "ods", "csv", "tsv", "numbers"],
    "pdf": ["pdf"],
    "image": ["png", "jpg", "jpeg", "svg", "gif", "tiff", "webp", "bmp", "heic", "ico"],
    "video": ["mp4", "mov", "avi", "mkv", "webm", "wmv"],
    "audio": ["mp3", "wav", "ogg", "aac", "flac", "m4a"],
    "archive": ["zip", "tar", "gz", "rar", "7z", "bz2"],
}

FILE_CATEGORY_CHOICES = [
    ("doc", _("Text document")),
    ("powerpoint", _("Slides")),
    ("calc", _("Spreadsheet")),
    ("pdf", "PDF"),
    ("image", _("Image")),
    ("video", _("Video")),
    ("audio", _("Audio")),
    ("archive", _("Archive")),
    ("other", _("Other")),
]
