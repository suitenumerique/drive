"""Tasks related to storage."""

from functools import cache
import logging

from django.conf import settings
from django.core.files.storage import default_storage

import boto3
import botocore

from drive.celery_app import app

logger = logging.getLogger(__name__)


class MissingMirroringConfigurationError(ValueError):
    """Exception raised when the mirroring S3 bucket configuration is missing."""

@cache
def get_mirror_s3_client():
    """Get the S3 client for the mirroring S3 bucket."""
    if (
        not settings.AWS_S3_MIRRORING_ACCESS_KEY_ID
        or not settings.AWS_S3_MIRRORING_SECRET_ACCESS_KEY
        or not settings.AWS_S3_MIRRORING_ENDPOINT_URL
    ):
        raise MissingMirroringConfigurationError(
            "Missing required configuration for mirroring S3 bucket"
        )

    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_S3_MIRRORING_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_S3_MIRRORING_SECRET_ACCESS_KEY,
        endpoint_url=settings.AWS_S3_MIRRORING_ENDPOINT_URL,
        config=botocore.client.Config(
            region_name=settings.AWS_S3_MIRRORING_REGION_NAME,
            signature_version=settings.AWS_S3_MIRRORING_SIGNATURE_VERSION,
            request_checksum_calculation=settings.AWS_S3_MIRRORING_REQUEST_CHECKSUM_CALCULATION,
            response_checksum_validation=settings.AWS_S3_MIRRORING_RESPONSE_CHECKSUM_VALIDATION,
        ),
    )


@app.task
def mirror_file(name):
    """Copy the file to the mirroring S3 bucket."""
    try:
        mirror_s3_client = get_mirror_s3_client()
    except MissingMirroringConfigurationError:
        logger.info("Mirroring S3 bucket is not configured, skipping mirroring")
        return

    mirror_bucket = settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME

    logger.info("Starting mirror of file %s to bucket %s", name, mirror_bucket)

    with default_storage.open(name, mode="rb") as source_file:
        mirror_s3_client.put_object(
            Bucket=mirror_bucket,
            Key=name,
            Body=source_file,
        )

    logger.info("Successfully mirrored file %s to bucket %s", name, mirror_bucket)
