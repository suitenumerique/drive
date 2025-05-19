"""Management command to get or set the CORS configuration of the storage bucket"""

import json

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from botocore.exceptions import ClientError


class Command(BaseCommand):
    """
    Management command to get or set the CORS configuration of the storage bucket
    """

    help = "Get or set the CORS configuration of the storage bucket based on the Django settings"

    def add_arguments(self, parser):
        """Adds the command-line argument to the command"""
        parser.add_argument(
            "--set", action="store_true", help="Set the CORS configuration"
        )

    def handle(self, *args, **options):
        """Handles the command"""

        s3_client = default_storage.connection.meta.client

        if options["set"]:
            # Set CORS rules
            if "*" in settings.ALLOWED_HOSTS:
                allowed_origins = ["*"]
            elif len(settings.ALLOWED_HOSTS) > 0:
                allowed_origins = [f"https://{h}" for h in settings.ALLOWED_HOSTS]
            else:
                raise ValueError("DJANGO_ALLOWED_HOSTS is not set")

            cors_config = {
                "CORSRules": [
                    {
                        "AllowedOrigins": allowed_origins,
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "HEAD", "POST", "PUT", "DELETE"],
                        "MaxAgeSeconds": 3000,
                        "ExposeHeaders": ["Etag"],
                    }
                ]
            }

            s3_client.put_bucket_cors(
                Bucket=default_storage.bucket_name, CORSConfiguration=cors_config
            )
            self.stdout.write(
                self.style.SUCCESS("CORS configuration successfully updated.")
            )
        else:
            # Get CORS rules
            try:
                cors = s3_client.get_bucket_cors(Bucket=default_storage.bucket_name)
                self.stdout.write(self.style.SUCCESS("CORS Configuration:"))
                self.stdout.write(json.dumps(cors, indent=2))
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchCORSConfiguration":
                    self.stdout.write(
                        self.style.WARNING(
                            "No CORS configuration found for this bucket."
                        )
                    )
                else:
                    self.stderr.write(
                        self.style.ERROR(f"Error fetching CORS config: {e}")
                    )
