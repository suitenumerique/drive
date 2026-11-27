"""Tests for document thumbnail generation."""

from datetime import UTC, datetime
from io import BytesIO
from unittest import mock

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

import pytest
from PIL import Image

from core import factories, models
from wopi.conversion import thumbnails
from wopi.conversion.backends.collabora import CollaboraConversionBackend
from wopi.conversion.backends.onlyoffice import OnlyOfficeConversionBackend
from wopi.conversion.exceptions import ConversionProviderError
from wopi.tasks.configure_wopi import WOPI_CONFIGURATION_CACHE_KEY

pytestmark = pytest.mark.django_db


def _configure_wopi(settings, clients, renderable=None):
    """Configure WOPI clients with their options, each rendering .docx and PDF by default."""
    settings.WOPI_CLIENTS = list(clients)
    settings.WOPI_CLIENTS_CONFIGURATION = {
        client: {"options": options} for client, options in clients.items()
    }
    renderable = renderable or {
        client: {"extensions": {"docx"}, "mimetypes": {"application/pdf"}} for client in clients
    }
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {},
            "extensions": {},
            **{
                client: {"proof_keys": {}, "renderable": formats}
                for client, formats in renderable.items()
            },
        },
    )


def _render_time(hour):
    """Fix the time a thumbnail is rendered at, without freezing the S3 request signing."""
    return mock.patch(
        "wopi.conversion.thumbnails.timezone.now",
        return_value=datetime(2024, 10, 3, hour, tzinfo=UTC),
    )


def _png(width, height):
    """Return the bytes of a blank PNG image."""
    buffer = BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _file(filename="report.docx"):
    """Create a ready file."""
    return factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename=filename,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )


def test_resolve_thumbnail_backend_requires_opt_in(settings):
    """A ConvertServiceUrl alone, set for legacy conversion, does not enable thumbnails."""
    _configure_wopi(
        settings,
        {"onlyoffice": {"ConvertServiceUrl": "http://onlyoffice/converter"}},
    )

    assert thumbnails.resolve_thumbnail_backend(_file()) is None


def test_resolve_thumbnail_backend_ignores_unknown_client(settings):
    """A client without a known backend cannot render thumbnails."""
    _configure_wopi(settings, {"vendorA": {"ThumbnailServiceUrl": "https://vendorA.example"}})

    assert thumbnails.resolve_thumbnail_backend(_file()) is None


@pytest.mark.parametrize("client_configuration", [None, {"proof_keys": {}}])
def test_resolve_thumbnail_backend_refreshes_stale_configuration(settings, client_configuration):
    """Formats unknown for a client opting in retry the render and refresh the configuration.

    A configuration cached by an earlier version lists no formats, nor does one whose
    discovery of the client has not succeeded yet.
    """
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    configuration = cache.get(WOPI_CONFIGURATION_CACHE_KEY)
    if client_configuration is None:
        del configuration["collabora"]
    else:
        configuration["collabora"] = client_configuration
    cache.set(WOPI_CONFIGURATION_CACHE_KEY, configuration)

    item = _file()
    with mock.patch("wopi.conversion.thumbnails.configure_wopi_clients") as configure:
        for _ in range(2):
            with pytest.raises(ConversionProviderError):
                thumbnails.resolve_thumbnail_backend(item)

    # Concurrent renders queue a single refresh.
    configure.delay.assert_called_once_with()


def test_resolve_thumbnail_backend_picks_first_client_opting_in(settings):
    """The first client defining a ThumbnailServiceUrl renders thumbnails."""
    _configure_wopi(
        settings,
        {
            "collabora": {},
            "onlyoffice": {"ThumbnailServiceUrl": "http://onlyoffice/converter"},
        },
    )

    backend = thumbnails.resolve_thumbnail_backend(_file())

    assert isinstance(backend, OnlyOfficeConversionBackend)
    assert backend.convert_service_url == "http://onlyoffice/converter"


def test_resolve_thumbnail_backend_picks_client_rendering_the_format(settings):
    """A format only the second client opens is rendered by that client, not the first."""
    _configure_wopi(
        settings,
        {
            "collabora": {"ThumbnailServiceUrl": "http://collabora"},
            "onlyoffice": {"ThumbnailServiceUrl": "http://onlyoffice/converter"},
        },
        renderable={
            "collabora": {"extensions": {"docx"}, "mimetypes": set()},
            "onlyoffice": {"extensions": {"docx", "djvu"}, "mimetypes": set()},
        },
    )

    assert isinstance(
        thumbnails.resolve_thumbnail_backend(_file("report.docx")), CollaboraConversionBackend
    )
    assert isinstance(
        thumbnails.resolve_thumbnail_backend(_file("scan.djvu")), OnlyOfficeConversionBackend
    )
    assert thumbnails.resolve_thumbnail_backend(_file("notes.xyz")) is None


@pytest.mark.parametrize(
    "filename,mimetype",
    [
        ("REPORT.DOCX", "application/octet-stream"),
        ("report", "application/pdf"),
        ("report.pdf", "application/pdf"),
    ],
)
def test_resolve_thumbnail_backend_matches_extension_or_mimetype(settings, filename, mimetype):
    """Formats are matched by case-insensitive extension, then by mimetype, PDF included."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file(filename)
    item.mimetype = mimetype

    assert isinstance(thumbnails.resolve_thumbnail_backend(item), CollaboraConversionBackend)


def test_is_thumbnail_pending_for_rendered_format_without_thumbnail(settings):
    """A ready file a client renders is pending until its thumbnail is recorded."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file("REPORT.DOCX")
    configuration = cache.get(WOPI_CONFIGURATION_CACHE_KEY)

    assert thumbnails.is_thumbnail_pending(item, configuration) is True

    item.thumbnail_updated_at = datetime(2024, 10, 3, tzinfo=UTC)
    assert thumbnails.is_thumbnail_pending(item, configuration) is False


@pytest.mark.parametrize(
    "filename,mimetype,upload_state",
    [
        ("notes.xyz", "application/octet-stream", models.ItemUploadStateChoices.READY),
        ("photo.png", "image/png", models.ItemUploadStateChoices.READY),
        ("report.docx", "application/octet-stream", models.ItemUploadStateChoices.ANALYZING),
    ],
)
def test_is_thumbnail_pending_not_for_unrendered_items(settings, filename, mimetype, upload_state):
    """Formats no client renders, browser images and files not ready are never pending."""
    _configure_wopi(
        settings,
        {"collabora": {"ThumbnailServiceUrl": "http://collabora"}},
        renderable={"collabora": {"extensions": {"docx", "png"}, "mimetypes": set()}},
    )
    item = _file(filename)
    item.mimetype = mimetype
    item.upload_state = upload_state

    assert thumbnails.is_thumbnail_pending(item, cache.get(WOPI_CONFIGURATION_CACHE_KEY)) is False


def test_is_thumbnail_pending_skips_unknown_formats_without_refresh(settings):
    """A client whose formats are unknown is skipped, with no configuration refresh."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    configuration = cache.get(WOPI_CONFIGURATION_CACHE_KEY)
    del configuration["collabora"]

    with mock.patch("wopi.conversion.thumbnails.configure_wopi_clients") as configure:
        assert thumbnails.is_thumbnail_pending(_file(), configuration) is False

    configure.delay.assert_not_called()


def test_is_thumbnail_pending_requires_opt_in(settings):
    """Without a client defining a ThumbnailServiceUrl, nothing is pending."""
    _configure_wopi(settings, {"collabora": {}})

    assert (
        thumbnails.is_thumbnail_pending(_file(), cache.get(WOPI_CONFIGURATION_CACHE_KEY)) is False
    )


def test_generate_thumbnail_stores_resized_png(settings):
    """Store the rendered first page resized to WOPI_THUMBNAIL_SIZE and record when."""
    settings.WOPI_THUMBNAIL_SIZE = 64
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file()
    assert item.thumbnail_key is None

    with (
        mock.patch.object(
            CollaboraConversionBackend,
            "thumbnail",
            side_effect=lambda *_: ContentFile(_png(800, 1200)),
        ),
        _render_time(12),
    ):
        assert thumbnails.generate_thumbnail(item) is True

    item.refresh_from_db()
    assert item.thumbnail_key == f"item/{item.id!s}/thumbnail/1727956800000.png"
    with default_storage.open(item.thumbnail_key) as file:
        assert Image.open(file).size == (43, 64)


def test_generate_thumbnail_replaces_previous_thumbnail(settings):
    """A new render gets a new key, so browsers cannot serve the old one from cache."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file()

    with mock.patch.object(
        CollaboraConversionBackend,
        "thumbnail",
        side_effect=lambda *_: ContentFile(_png(80, 120)),
    ):
        with _render_time(12):
            thumbnails.generate_thumbnail(item)
        previous_key = item.thumbnail_key
        with _render_time(13):
            thumbnails.generate_thumbnail(item)
        # Rendering twice within the same millisecond keeps a single file.
        with _render_time(13):
            thumbnails.generate_thumbnail(item)

    item.refresh_from_db()
    assert item.thumbnail_key != previous_key
    assert default_storage.exists(item.thumbnail_key)
    assert not default_storage.exists(previous_key)
    _dirs, files = default_storage.listdir(f"item/{item.id!s}/thumbnail")
    assert files == [item.thumbnail_key.rsplit("/", 1)[1]]


def test_generate_thumbnail_render_started_later_wins(settings):
    """An overlapping render that started earlier but finishes last keeps no file."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file()
    stale_item = models.Item.objects.get(pk=item.pk)

    with mock.patch.object(
        CollaboraConversionBackend,
        "thumbnail",
        side_effect=lambda *_: ContentFile(_png(80, 120)),
    ):
        with _render_time(13):
            assert thumbnails.generate_thumbnail(item) is True
        with _render_time(12):
            assert thumbnails.generate_thumbnail(stale_item) is False

    item.refresh_from_db()
    assert item.thumbnail_key == f"item/{item.id!s}/thumbnail/1727960400000.png"
    _dirs, files = default_storage.listdir(f"item/{item.id!s}/thumbnail")
    assert files == ["1727960400000.png"]


def test_generate_thumbnail_drops_renders_that_lost(settings):
    """Files left by earlier overlapping renders are removed, later ones are kept."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file()
    folder = f"item/{item.id!s}/thumbnail"
    # 11:00 lost against a render still running, 14:00 belongs to one not committed yet.
    default_storage.save(f"{folder}/1727953200000.png", ContentFile(_png(8, 8)))
    default_storage.save(f"{folder}/1727964000000.png", ContentFile(_png(8, 8)))

    with (
        mock.patch.object(
            CollaboraConversionBackend, "thumbnail", return_value=ContentFile(_png(80, 120))
        ),
        _render_time(12),
    ):
        assert thumbnails.generate_thumbnail(item) is True

    _dirs, files = default_storage.listdir(folder)
    assert sorted(files) == ["1727956800000.png", "1727964000000.png"]


def test_generate_thumbnail_does_not_depend_on_the_creator(settings):
    """Thumbnails are rendered for ready files whose creator is gone."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file()
    item.creator = None

    with mock.patch.object(
        CollaboraConversionBackend, "thumbnail", return_value=ContentFile(_png(80, 120))
    ):
        assert thumbnails.generate_thumbnail(item) is True


@pytest.mark.parametrize(
    "upload_state",
    [
        models.ItemUploadStateChoices.ANALYZING,
        models.ItemUploadStateChoices.SUSPICIOUS,
        models.ItemUploadStateChoices.FILE_TOO_LARGE_TO_ANALYZE,
    ],
)
def test_generate_thumbnail_skips_files_not_ready(settings, upload_state):
    """Only ready files get a thumbnail."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="report.docx",
        update_upload_state=upload_state,
    )

    with mock.patch.object(CollaboraConversionBackend, "thumbnail") as thumbnail:
        assert thumbnails.generate_thumbnail(item) is False

    thumbnail.assert_not_called()


def test_generate_thumbnail_skips_unsupported_item(settings):
    """Files no WOPI client opens get no thumbnail."""
    _configure_wopi(settings, {"collabora": {"ThumbnailServiceUrl": "http://collabora"}})
    item = _file("photo.png")

    with mock.patch.object(CollaboraConversionBackend, "thumbnail") as thumbnail:
        assert thumbnails.generate_thumbnail(item) is False

    thumbnail.assert_not_called()
    item.refresh_from_db()
    assert item.thumbnail_updated_at is None


def test_generate_thumbnail_skips_browser_images(settings):
    """Images the browser previews keep their preview, even when the client renders them."""
    _configure_wopi(
        settings,
        {"collabora": {"ThumbnailServiceUrl": "http://collabora"}},
        renderable={"collabora": {"extensions": {"png"}, "mimetypes": set()}},
    )
    item = _file("photo.png")
    item.mimetype = "image/png"

    with mock.patch.object(CollaboraConversionBackend, "thumbnail") as thumbnail:
        assert thumbnails.generate_thumbnail(item) is False

    thumbnail.assert_not_called()
