# DS Proxy

DS Proxy is an encryption HTTP Proxy compatible with the S3 API. Its goal is to encrypt all the objects you upload on your S3 compatible object storage and then decrypt it when you download them.

This solution allow you to safely store the files uploaded on drive by just change the S3 configuration in your settings.

You can find a complete description of this Proxy on its github repository (but in french) : [https://github.com/demarche-numerique/ds_proxy](https://github.com/demarche-numerique/ds_proxy)

By default the compose environment and the development helm chart env do not enable ds_proxy. They are present as an example and can be easily enabled.

### Known issues

Drive is using [boto3](https://boto3.amazonaws.com), the official AWS SDK, as client to manage files with the S3 compatible object storage you decided to use.
The SDK is using some improvements to enhance performance but they are not compatible with DS Proxy.
The SDK is able to switch between single or multipart data for both the upload and the download.

To disable this behaviour you have to configure boto3 using environment variable.

For the upload, set these environment variables:

```
AWS_REQUEST_CHECKSUM_CALCULATION: when_required
AWS_RESPONSE_CHECKSUM_VALIDATION: when_required
```

For the download, set this environment variables:

```
S3_TRANSFER_CONFIG_USE_THREADS: False
S3_TRANSFER_CONFIG_MULTIPART_THRESHOLD: "10737418240"
S3_TRANSFER_CONFIG_MULTIPART_CHUNKSIZE: "10737418240"
S3_TRANSFER_CONFIG_MAX_CONCURRENCY: 1
```

### Enable ds_proxy with docker compose

You have to change the settings related to S3 in the `env.d/development/common.local` file:

```
AWS_S3_DOMAIN_REPLACE=http://localhost:4444/upstream
AWS_S3_ENDPOINT_URL=http://ds-proxy:4444/upstream
```

You also have to change the nginx config present in `docker/files/development/etc/nginx/conf.d/default.conf`. In the file comment the minio config and uncomment the DS Proxy config. Present twice in `location /media/` and `location /media/preview` blocks:

```
# Get resource from Minio
# proxy_pass http://minio:9000/drive-media-storage/;
# proxy_set_header Host minio:9000;
# To use with ds_proxy
proxy_pass http://ds-proxy:4444/upstream/drive-media-storage/;
proxy_set_header Host ds-proxy:4444;
```

Then start the django stack running `make run-backend`.
Finally, start ds_proxy: `docker compose up -d ds-proxy`

That's all, ds_proxy is running and Drive configured to use it. All the file uploaded will be encrypted and then decrypted when you download them.

### Enable ds_proxy with tilt

Once you have an up and running stack with tilt, you can enable ds_proxy and configure drive to use it.

In the `src/helm/helmfile.yaml` file change the `ds_proxy.enabled` value to `true`.
Then in the `src/helm/env.d/dev/values.drive.yaml.gotmpl` file you will have to comment/uncomment these variables:
    - `AWS_S3_ENDPOINT_URL`
    - `nginx.ingress.kubernetes.io/upstream-vhost` (present twice)
    - `host` (in the `serviceMedia`)

Reloading the tilt stack should deploy DS Proxy.
