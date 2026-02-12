# Mirror objects on two buckets

It is possible to mirror objects uploaded on two different backup.
The initial reason we introduce this feature was to make a migration between two different bucket on two different cloud service provider without any downtime.

For now, this feature only mirror and is not able to read the object on the two buckets. Only the main bucket is used for this.

## Requirement

You must deploy a celery worker, mirroring is made asynchronously using tasks.

## Configuration

For the main object storage, you have nothing to change if you are already using it, no change is needed. 
For the second object storage, used for mirroring, you have to set this settings : 

- `AWS_S3_MIRRORING_ACCESS_KEY_ID` : AWS S3 access key id for the mirroring bucket. Mandatory
- `AWS_S3_MIRRORING_SECRET_ACCESS_KEY` : AWS S3 secret access key for the mirroring bucket. Mandatory
- `AWS_S3_MIRRORING_STORAGE_BUCKET_NAME` : AWS S3 bucket name for the mirroring bucket. Mandatory
- `AWS_S3_MIRRORING_ENDPOINT_URL` : AWS S3 endpoint url for the mirroring bucket. Mandatory
- `AWS_S3_MIRRORING_REGION_NAME` : AWS S3 region name for the mirroring bucket. Mandatory
- `AWS_S3_MIRRORING_SIGNATURE_VERSION` : AWS S3 signature version for the mirroring bucket. Set to `s3v4`, change it only if needed.
- `AWS_S3_MIRRORING_REQUEST_CHECKSUM_CALCULATION` : AWS S3 request checksum calculation config for the mirroring bucket. Set to `when_supported`. Change it only if needed
- `AWS_S3_MIRRORING_RESPONSE_CHECKSUM_VALIDATION` : AWS S3 response checksum calculation config for the mirroring bucket Set to `when_supported`. Change it only if needed

Once the mirror object storage configured, you have to change the storage class to use. set this settings

- `STORAGES_DEFAULT_BACKEND` to `core.storage.s3_mirroring_storage.S3MirroringStorage`

## Migrate from one bucket to the other.

The mirroring feature has been developed to ease the migration from one bucket located in one cloud provider to an other bucket located in an other cloud provider. 

The scenario to makge the migration is this one :

- Enable the mirroring by configuring it (see documentation before). The mirrored bucket should be the future one used after the migration completed
- Run the management command `prepare_mirroring_items_history`, its purpose is to put in the `mirror_item_task` all the existing items in order to mirror them
- Then, run the management command `process_pending_mirror_tasks` periodically. This management command will put in a celery queue the tasks to process by batch of 100 items. You can configure a cron to trigger this management command every 5 or 10 minutes for example. You should monitor it to determint the interval between tasks.
