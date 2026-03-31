"""Tasks related to storage."""

import logging
from functools import cache

from django.conf import settings
from django.core.files.storage import default_storage

import boto3
import botocore

from core.api.utils import get_item_file_head_object
from core.models import Item, MirrorItemTask, MirrorItemTaskStatusChoices

from drive.celery_app import app

logger = logging.getLogger(__name__)


@cache
def get_mirror_s3_client():
    """Get the S3 client for the mirroring S3 bucket."""
    if (
        not settings.AWS_S3_MIRRORING_ACCESS_KEY_ID
        or not settings.AWS_S3_MIRRORING_SECRET_ACCESS_KEY
        or not settings.AWS_S3_MIRRORING_ENDPOINT_URL
    ):
        return None

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


@app.task(bind=True, max_retries=10)
def mirror_file(self, mirror_task_id):
    """Copy the file to the mirroring S3 bucket."""
    mirror_s3_client = get_mirror_s3_client()
    if not mirror_s3_client:
        logger.info("Mirroring S3 bucket is not configured, skipping mirroring")
        return

    try:
        mirror_task = MirrorItemTask.objects.select_related("item").get(id=mirror_task_id)
    except MirrorItemTask.DoesNotExist:
        logger.error("Mirror task %s does not exist", mirror_task_id)
        return

    if mirror_task.status != MirrorItemTaskStatusChoices.PENDING:
        logger.info("Mirror task %s is not pending, skipping mirroring", mirror_task_id)
        return

    mirror_task.status = MirrorItemTaskStatusChoices.PROCESSING
    mirror_task.save(update_fields=["status", "updated_at"])
    item_key = mirror_task.item.file_key

    mirror_bucket = settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME

    logger.info("Starting mirror of file %s to bucket %s", item_key, mirror_bucket)

    try:
        head_object = get_item_file_head_object(mirror_task.item)
        with default_storage.open(item_key, mode="rb") as source_file:
            mirror_s3_client.put_object(
                Bucket=mirror_bucket,
                Key=item_key,
                Body=source_file,
                ContentType=mirror_task.item.mimetype,
                Metadata=head_object["Metadata"],
            )
    except (
        boto3.exceptions.Boto3Error,
        botocore.exceptions.BotoCoreError,
        botocore.exceptions.ClientError,
    ) as exc:
        if self.request.retries >= self.max_retries:
            mirror_task.status = MirrorItemTaskStatusChoices.FAILED
            mirror_task.error_details = str(exc)
            mirror_task.save(update_fields=["status", "error_details", "updated_at"])
            return

        mirror_task.status = MirrorItemTaskStatusChoices.PENDING
        mirror_task.retries = mirror_task.retries + 1
        mirror_task.save(update_fields=["status", "updated_at", "retries"])

        logger.info(
            "Failed mirroring file %s to bucket %s. Task will be retry, %s retries already occured",
            item_key,
            mirror_bucket,
            self.request.retries,
        )

        self.retry(exc=exc)

    logger.info("Successfully mirrored file %s to bucket %s", item_key, mirror_bucket)
    mirror_task.status = MirrorItemTaskStatusChoices.COMPLETED
    mirror_task.save(update_fields=["status", "updated_at"])


@app.task
def rename_file_on_mirroring_bucket(item_id, from_file_key, to_file_key):
    """
    Rename a file on the mirroring bucket. If the original file does not exist, mirror it.
    Copy it otherwise
    """
    mirror_s3_client = get_mirror_s3_client()
    if not mirror_s3_client:
        logger.info(
            "Mirroring S3 bucket is not configured, skipping renaming file on the mirroring bucket"
        )
        return
    mirror_bucket = settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME

    try:
        mirror_s3_client.head_object(Bucket=mirror_bucket, Key=from_file_key)
    except botocore.exceptions.ClientError:
        item = Item.objects.get(pk=item_id)
        mirror_task = MirrorItemTask.objects.create(
            item=item, status=MirrorItemTaskStatusChoices.PENDING
        )

        mirror_file.delay(mirror_task.id)
        return

    mirror_s3_client.copy_object(
        Bucket=mirror_bucket,
        CopySource={
            "Bucket": mirror_bucket,
            "Key": from_file_key,
        },
        Key=to_file_key,
        MetadataDirective="COPY",
    )
    mirror_s3_client.delete_object(
        Bucket=mirror_bucket,
        Key=from_file_key,
    )


@app.task
def duplicate_file_on_mirroring_bucket(duplicated_item_id, from_file_key, to_file_key):
    """Duplicate a file on the mirror bucket by creating a copy of the original file."""

    mirror_s3_client = get_mirror_s3_client()
    if not mirror_s3_client:
        logger.info(
            "Mirroring S3 bucket is not configured, skipping renaming file on the mirroring bucket"
        )
        return
    mirror_bucket = settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME

    try:
        mirror_s3_client.head_object(Bucket=mirror_bucket, Key=from_file_key)
    except botocore.exceptions.ClientError:
        item = Item.objects.get(pk=duplicated_item_id)
        mirror_task = MirrorItemTask.objects.create(
            item=item, status=MirrorItemTaskStatusChoices.PENDING
        )

        mirror_file.delay(mirror_task.id)
        return

    mirror_s3_client.copy_object(
        Bucket=mirror_bucket,
        CopySource={
            "Bucket": mirror_bucket,
            "Key": from_file_key,
        },
        Key=to_file_key,
        MetadataDirective="COPY",
    )
