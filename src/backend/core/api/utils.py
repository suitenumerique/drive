"""Util to generate S3 authorization headers for object storage access control"""

from django.conf import settings
from django.core.files.storage import default_storage

import botocore


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

    # Generate the policy
    s3_client = default_storage.connection.meta.client
    policy = s3_client.generate_presigned_post(
        default_storage.bucket_name,
        key,
        Fields={"acl": "private"},
        Conditions=[
            {"acl": "private"},
            ["content-length-range", 0, settings.ITEM_FILE_MAX_SIZE],
        ],
        ExpiresIn=settings.AWS_S3_UPLOAD_POLICY_EXPIRATION,
    )

    return policy
