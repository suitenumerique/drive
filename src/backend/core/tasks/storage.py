"""Tasks related to storage."""

from drive.celery_app import app


@app.task
def mirror_file(name):
    """Mirror the file on the other S3 buckets."""
    pass
