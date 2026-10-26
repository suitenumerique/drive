# Installation
If you want to install Drive you've come to the right place.

For now we only have a documentation to install it on Kubernetes. We will more than happy to improve this documentation with other methods.

Feel free to make a PR to add ones that are not listed after 🙏

## Kubernetes
We (Drive maintainers) are only using the Kubernetes deployment method in production. We can only provide advanced support for this method.
Please follow the instructions laid out [here](/docs/installation/kubernetes.md).

## Installation on NixOS

[lasuite-drive](https://search.nixos.org/packages?channel=unstable&query=lasuite-drive#show=lasuite-drive) is packaged in Nixpkgs and provides a NixOS module under services.lasuite-drive.

### Example configuration
The following example enables La Suite Drive with local PostgreSQL and Redis instances, an S3-compatible object storage service, and an OpenID Connect provider:
```
services.lasuite-drive = {
  enable = true;
  domain = "drive";

  postgresql.createLocally = true;
  redis.createLocally = true;

  s3Url = "https://s3.drive/";

  environmentFiles = [
    "/run/garage-credentials/drive.env"
    "/run/keycloak-credentials/drive.env"
  ];

  settings = {
    AWS_S3_ENDPOINT_URL = "https://s3.drive";
    AWS_S3_REGION_NAME = "garage";
    AWS_STORAGE_BUCKET_NAME = "drive";

    OIDC_RP_CLIENT_ID = "drive";
    OIDC_OP_JWKS_ENDPOINT = "https://auth.drive/realms/drive/protocol/openid-connect/certs";
    OIDC_OP_AUTHORIZATION_ENDPOINT = "https://auth.drive/realms/drive/protocol/openid-connect/auth";
    OIDC_OP_TOKEN_ENDPOINT = "https://auth.drive/realms/drive/protocol/openid-connect/token";
    OIDC_OP_USER_ENDPOINT = "https://auth.drive/realms/drive/protocol/openid-connect/userinfo";
    OIDC_OP_LOGOUT_ENDPOINT = "https://auth.drive/realms/drive/protocol/openid-connect/logout";

    REQUESTS_CA_BUNDLE = "/run/nginx-certs/dreamland_cert_root";
  };
};

systemd.services = {
  lasuite-drive.wants = ["network-online.target"];
  lasuite-drive-celery.wants = ["network-online.target"];
  lasuite-drive-beat.wants = ["network-online.target"];
};
```
Secrets such as S3 credentials and the OIDC client secret can be provided through environmentFiles.

### Options Reference

| Option                                            | Description                                                                                                           | Default Value |
|---------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|---------------|
| `services.lasuite-drive.enable`                   | Enable the La Suite Drive service                                                                                     | `false`       |
| `services.lasuite-drive.enableNginx`              | Configure an nginx virtual host for La Suite Drive                                                                    | `false`       |
| `services.lasuite-drive.domain`                   | Domain name used by La Suite Drive                                                                                    |               |
| `services.lasuite-drive.s3Url`                    | URL of the S3-compatible object storage service                                                                       |               |
| `services.lasuite-drive.environmentFiles`         | Files containing environment variables and secrets passed to La Suite Drive                                           | `[]`’         |
| `services.lasuite-drive.settings`                 | Environment variables used to configure La Suite Drive                                                                | `{}`’         |
| `services.lasuite-drive.postgresql.createLocally` | Create and configure a local PostgreSQL database                                                                      | `false`       |
| `services.lasuite-drive.redis.createLocally`      | Create and configure a local Redis instance                                                                           | `false`       |


The complete list of available options for services.lasuite-drive is available in the [NixOS options search](https://search.nixos.org/options?channel=26.05&query=services.lasuite-drive&type=options#show=option%253Aservices.lasuite-drive).
