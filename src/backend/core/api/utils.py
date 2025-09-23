"""Util to generate S3 authorization headers for object storage access control"""

import mimetypes
from datetime import datetime

from django.conf import settings
from django.core.files.storage import default_storage

import boto3
import botocore


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
    return the policy and the headers to use to upload the file.
    """

    guessed_mime_type, _ = mimetypes.guess_type(item.filename)

    if not guessed_mime_type:
        raise ValueError("Could not guess the mime type of the item")

    params = {
        "Bucket": default_storage.bucket_name,
        "Key": item.file_key,
        "ACL": "private",
    }

    headers = {
        "X-amz-acl": "private",
    }

    if not _is_previewable(guessed_mime_type):
        params["ContentDisposition"] = f'attachment; filename="{item.filename:s}"'
        headers["Content-Disposition"] = f'attachment; filename="{item.filename:s}"'

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
        Params=params,
        ExpiresIn=settings.AWS_S3_UPLOAD_POLICY_EXPIRATION,
    )

    return policy, headers


def _is_previewable(mime_type):
    """
    Check if a mime type is previewable.
    """
    for allowed in settings.ITEM_PREVIEWABLE_MIME_TYPES:
        if allowed.endswith("/"):
            if mime_type.startswith(allowed):
                return True
        elif mime_type == allowed:
            return True
    return False
