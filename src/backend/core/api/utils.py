"""Util to generate S3 authorization headers for object storage access control"""

import logging
import mimetypes
from datetime import datetime

from django.conf import settings
from django.core.files.storage import default_storage

import boto3
import botocore
import magic

logger = logging.getLogger(__name__)


def flat_to_nested(items):
    """
    Create a nested tree structure from a flat list of items.
    """
    # Create a dictionary to hold nodes by their path
    node_dict = {}
    roots = []

    def sort_key(serialized_item):
        return serialized_item["depth"], datetime.fromisoformat(
            serialized_item["created_at"]
        )

    # Sort the flat list by path to ensure parent nodes are processed first
    items.sort(key=sort_key)

    for item in items:
        item["children"] = []  # Initialize children list
        node_dict[item["path"]] = item

        # Determine parent path
        parent_path = ".".join(item["path"].split(".")[:-1])

        if parent_path in node_dict:
            node_dict[parent_path]["children"].append(item)
        else:
            roots.append(item)  # Collect root nodes

    if len(roots) > 1:
        raise ValueError("More than one root element detected")

    return roots[0] if roots else {}


def filter_root_paths(paths, skip_sorting=False):
    """
    Filters root paths from a list of paths representing a tree structure.
    A root path is defined as a path that is not a prefix of any other path.

    Args:
        paths (list of PathValue): The list of paths.

    Returns:
        list of str: The filtered list of root paths.
    """
    if not skip_sorting:
        paths.sort()

    root_paths = []
    for path in paths:
        # If the current path is not a prefix of the last added root path, add it
        if not root_paths or not str(path).startswith(str(root_paths[-1])):
            root_paths.append(path)

    return root_paths


def generate_s3_authorization_headers(key):
    """
    Generate authorization headers for an s3 object.
    These headers can be used as an alternative to signed urls with many benefits:
    - the urls of our files never expire and can be stored in our items' content
    - we don't leak authorized urls that could be shared (file access can only be done
      with cookies)
    - access control is truly realtime
    - the object storage service does not need to be exposed on internet
    """
    url = default_storage.unsigned_connection.meta.client.generate_presigned_url(
        "get_object",
        ExpiresIn=0,
        Params={"Bucket": default_storage.bucket_name, "Key": key},
    )
    request = botocore.awsrequest.AWSRequest(method="get", url=url)

    s3_client = default_storage.connection.meta.client
    # pylint: disable=protected-access
    credentials = s3_client._request_signer._credentials  # noqa: SLF001
    frozen_credentials = credentials.get_frozen_credentials()
    region = s3_client.meta.region_name
    auth = botocore.auth.S3SigV4Auth(frozen_credentials, "s3", region)
    auth.add_auth(request)

    return request


def generate_upload_policy(item):
    """
    Generate a S3 upload policy for a given item.
    """

    # Generate a unique key for the item
    key = f"{item.key_base}/{item.filename}"

    # This settings should be used if the backend application and the frontend application
    # can't connect to the object storage with the same domain. This is the case in the
    # docker compose stack used in development. The frontend application will use localhost
    # to connect to the object storage while the backend application will use the object storage
    # service name declared in the docker compose stack.
    # This is needed because the domain name is used to compute the signature. So it can't be
    # changed dynamically by the frontend application.
    if settings.AWS_S3_DOMAIN_REPLACE:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_DOMAIN_REPLACE,
            config=botocore.client.Config(
                region_name=settings.AWS_S3_REGION_NAME,
                signature_version=settings.AWS_S3_SIGNATURE_VERSION,
            ),
        )
    else:
        s3_client = default_storage.connection.meta.client

    # Generate the policy
    policy = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": default_storage.bucket_name, "Key": key, "ACL": "private"},
        ExpiresIn=settings.AWS_S3_UPLOAD_POLICY_EXPIRATION,
    )

    return policy


def is_previewable_item(item):
    """
    Check if a mime type is previewable.
    """
    if item.mimetype is None:
        return False

    for allowed in settings.ITEM_PREVIEWABLE_MIME_TYPES:
        if allowed.endswith("/"):
            if item.mimetype.startswith(allowed):
                return True
        elif item.mimetype == allowed:
            return True
    return False


def get_item_file_head_object(item):
    """
    Get the head object of an item file.
    """
    return default_storage.connection.meta.client.head_object(
        Bucket=default_storage.bucket_name, Key=item.file_key
    )


def detect_mimetype(file_buffer: bytes, filename: str | None = None) -> str:
    """
    Detect MIME type using multiple methods for better accuracy.

    This function combines:
    1. Magic bytes detection (python-magic) - most reliable for actual file content
    2. File extension detection (mimetypes) - useful as fallback or for validation

    Args:
        file_buffer: The file content buffer (first bytes of the file)
        filename: Optional filename to extract extension from

    Returns:
        str: The detected MIME type
    """
    # Initialize magic detector
    mime_detector = magic.Magic(mime=True)

    # Method 1: Detect from file content (magic bytes) - most reliable
    mimetype_from_content = mime_detector.from_buffer(file_buffer)

    # If we have a filename, try extension-based detection as well
    mimetype_from_extension = None
    if filename:
        # Use mimetypes module to guess from extension
        # Use guess_file_type (Python 3.13+) instead of deprecated guess_type
        mimetype_from_extension, _ = mimetypes.guess_file_type(filename, strict=False)

    logger.info("detect_mimetype: mimetype_from_content: %s", mimetype_from_content)
    logger.info("detect_mimetype: mimetype_from_extension: %s", mimetype_from_extension)

    # Strategy: Prefer content-based detection, but use extension if:
    # 1. Content detection returns generic types (application/octet-stream, text/plain)
    # 2. Content detection fails or returns None
    # 3. Extension detection provides a more specific type

    # Generic/unreliable MIME types that we should try to improve
    generic_types = {
        "application/octet-stream",
        "application/zip",
        "text/plain",
    }

    # If content detection gives us a generic type and we have extension info
    if mimetype_from_content in generic_types and mimetype_from_extension:
        # Use extension-based detection if it's more specific
        if mimetype_from_extension not in generic_types:
            return mimetype_from_extension

    # If content detection failed, returned None or is a generic type, use extension if available
    if not mimetype_from_content or mimetype_from_content in generic_types:
        if mimetype_from_extension:
            return mimetype_from_extension

    # Default to content-based detection (most reliable)
    return mimetype_from_content or "application/octet-stream"
