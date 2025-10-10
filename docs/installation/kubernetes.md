# Installation on a Kubernetes (k8s) cluster

This document is a step-by-step guide that describes how to install Drive on a k8s cluster. It's a teaching document to learn how it works. It needs to be adapted for a production environment.

## Prerequisites

- k8s cluster with an nginx-ingress controller
- an OIDC provider (if you don’t have one, we provide an example)
- a PostgreSQL server (if you don’t have one, we provide an example)
- a Redis server (if you don’t have one, we provide an example)
- an S3 bucket (if you don’t have one, we provide an example)

### Test cluster

If you do not have a test cluster, you can install everything on a local Kind cluster. In this case, the simplest way is to use our script **bin/start-kind.sh**.

To be able to use the script, you need to install:

- Docker (https://docs.docker.com/desktop/)
- Kind (https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- Mkcert (https://github.com/FiloSottile/mkcert#installation)
- Helm (https://helm.sh/docs/intro/quickstart/#install-helm)

```
./bin/start-kind.sh
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  4700  100  4700    0     0  92867      0 --:--:-- --:--:-- --:--:-- 94000
0. Create ca
The local CA is already installed in the system trust store! 👍
The local CA is already installed in the Firefox and/or Chrome/Chromium trust store! 👍


Created a new certificate valid for the following names 📜
 - "127.0.0.1.nip.io"
 - "*.127.0.0.1.nip.io"

Reminder: X.509 wildcards only go one level deep, so this won’t match a.b.127.0.0.1.nip.io ℹ️

The certificate is at "./127.0.0.1.nip.io+1.pem" and the key at "./127.0.0.1.nip.io+1-key.pem" ✅

It will expire on 24 March 2027 🗓

1. Create registry container unless it already exists
2. Create kind cluster with containerd registry config dir enabled
Creating cluster "suite" ...
 ✓ Ensuring node image (kindest/node:v1.27.3) 🖼
 ✓ Preparing nodes 📦
 ✓ Writing configuration 📜
 ✓ Starting control-plane 🕹️
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
Set kubectl context to "kind-suite"
You can now use your cluster with:

kubectl cluster-info --context kind-suite

Thanks for using kind! 😊
3. Add the registry config to the nodes
4. Connect the registry to the cluster network if not already connected
5. Document the local registry
configmap/local-registry-hosting created
Warning: resource configmaps/coredns is missing the kubectl.kubernetes.io/last-applied-configuration annotation which is required by kubectl apply. kubectl apply should only be used on resources created declaratively by either kubectl create --save-config or kubectl apply. The missing annotation will be patched automatically.
configmap/coredns configured
deployment.apps/coredns restarted
6. Install ingress-nginx
namespace/ingress-nginx created
serviceaccount/ingress-nginx created
serviceaccount/ingress-nginx-admission created
role.rbac.authorization.k8s.io/ingress-nginx created
role.rbac.authorization.k8s.io/ingress-nginx-admission created
clusterrole.rbac.authorization.k8s.io/ingress-nginx created
clusterrole.rbac.authorization.k8s.io/ingress-nginx-admission created
rolebinding.rbac.authorization.k8s.io/ingress-nginx created
rolebinding.rbac.authorization.k8s.io/ingress-nginx-admission created
clusterrolebinding.rbac.authorization.k8s.io/ingress-nginx created
clusterrolebinding.rbac.authorization.k8s.io/ingress-nginx-admission created
configmap/ingress-nginx-controller created
service/ingress-nginx-controller created
service/ingress-nginx-controller-admission created
deployment.apps/ingress-nginx-controller created
job.batch/ingress-nginx-admission-create created
job.batch/ingress-nginx-admission-patch created
ingressclass.networking.k8s.io/nginx created
validatingwebhookconfiguration.admissionregistration.k8s.io/ingress-nginx-admission created
secret/mkcert created
deployment.apps/ingress-nginx-controller patched
7. Setup namespace
namespace/drive created
Context "kind-suite" modified.
secret/mkcert created
$ kubectl -n ingress-nginx get po
NAME                                        READY   STATUS      RESTARTS   AGE
ingress-nginx-admission-create-t55ph        0/1     Completed   0          2m56s
ingress-nginx-admission-patch-94dvt         0/1     Completed   1          2m56s
ingress-nginx-controller-57c548c4cd-2rx47   1/1     Running     0          2m56s
```

When your k8s cluster is ready (the ingress nginx controller is up), you can start the deployment. This cluster is special because it uses the `*.127.0.0.1.nip.io` domain and mkcert certificates to have full HTTPS support and easy domain name management.

The namespace `drive` is already created, you can work in it and configure your kubectl cli to use it by default.

```
$ kubectl config set-context --current --namespace=drive
```

Please remember that `*.127.0.0.1.nip.io` will always resolve to `127.0.0.1`, except in the k8s cluster where we configure CoreDNS to answer with the ingress-nginx service IP.

## Preparation

### What do you use to authenticate your users?

Drive uses OIDC, so if you already have an OIDC provider, obtain the necessary information to use it. In the next step, we will see how to configure Django (and thus Drive) to use it. If you do not have a provider, we will show you how to deploy a local Keycloak instance (this is not a production deployment, just a demo).

We provide our own Helm chart for all development dependencies, it is available here https://github.com/suitenumerique/helm-dev-backend
This provided chart is for development purposes only and is not ready to use in production.

You can install it on your cluster to deploy Keycloak, Minio, Postgresql and Redis.

```
$ helm install --repo https://suitenumerique.github.io/helm-dev-backend -f docs/examples/helm/keycloak.values.yaml keycloak dev-backend
$ #wait until
$ kubectl get pods
NAME                                 READY   STATUS    RESTARTS   AGE
keycloak-dev-backend-keycloak-0      1/1     Running   0          36s
keycloak-dev-backend-keycloak-pg-0   1/1     Running   0          36s
```

The important information you will need from here is:

```yaml
OIDC_OP_JWKS_ENDPOINT: https://drive-keycloak.127.0.0.1.nip.io/realms/drive/protocol/openid-connect/certs
OIDC_OP_AUTHORIZATION_ENDPOINT: https://drive-keycloak.127.0.0.1.nip.io/realms/drive/protocol/openid-connect/auth
OIDC_OP_TOKEN_ENDPOINT: https://drive-keycloak.127.0.0.1.nip.io/realms/drive/protocol/openid-connect/token
OIDC_OP_USER_ENDPOINT: https://drive-keycloak.127.0.0.1.nip.io/realms/drive/protocol/openid-connect/userinfo
OIDC_OP_LOGOUT_ENDPOINT: https://drive-keycloak.127.0.0.1.nip.io/realms/drive/protocol/openid-connect/logout
OIDC_RP_CLIENT_ID: drive
OIDC_RP_CLIENT_SECRET: ThisIsAnExampleKeyForDevPurposeOnly
OIDC_RP_SIGN_ALGO: RS256
OIDC_RP_SCOPES: "openid email"
OIDC_USER_FIELD_TO_SHORTNAME: "given_name"
OIDC_USER_FIELDS_TO_FULLNAME: "given_name,usual_name"
```

### Find redis server connection values

Drive needs a Redis server so we start by deploying one:

```
$ helm install --repo https://suitenumerique.github.io/helm-dev-backend -f docs/examples/helm/redis.values.yaml redis dev-backend
$ kubectl get pods
NAME                                       READY   STATUS    RESTARTS   AGE
keycloak-dev-backend-keycloak-0            1/1     Running   0          3m34s
keycloak-dev-backend-keycloak-pg-0         1/1     Running   0          3m34s
redis-dev-backend-redis-7cbd7c7bb8-6d74c   1/1     Running   0          14s
```

The important information you will need from here is:

```yaml
REDIS_URL: redis://user:pass@dev-backend-redis:6379/1
DJANGO_CELERY_BROKER_URL: redis://user:pass@dev-backend-redis:6379/1
```

### Find postgresql connection values

Drive uses a Postgresql database as backend, so if you have a provider, obtain the necessary information to use it. If you don't, you can install a postgresql testing environment as follow:

```
$ helm install --repo https://suitenumerique.github.io/helm-dev-backend -f docs/examples/helm/postgresql.values.yaml postgresql dev-backend
$ kubectl get pods
NAME                                       READY   STATUS    RESTARTS   AGE
keycloak-dev-backend-keycloak-0            1/1     Running   0          5m12s
keycloak-dev-backend-keycloak-pg-0         1/1     Running   0          5m12s
postgresql-dev-backend-postgres-0          0/1     Running   0          9s
redis-dev-backend-redis-7cbd7c7bb8-6d74c   1/1     Running   0          112s

```

The important information you will need from here is:

```yaml
DB_HOST: postgresql-dev-backend-postgres
DB_NAME:
    secretKeyRef:
    name: postgresql-dev-backend-postgres
    key: database
DB_USER:
    secretKeyRef:
    name: postgresql-dev-backend-postgres
    key: username
DB_PASSWORD:
    secretKeyRef:
    name: postgresql-dev-backend-postgres
    key: password
DB_PORT: 5432
```

### Find s3 bucket connection values

Drive uses an S3 bucket to store files, so if you have a provider, obtain the necessary information to use it. If you don't, you can install a local minio testing environment as follow:

```
$ helm install --repo https://suitenumerique.github.io/helm-dev-backend -f docs/examples/helm/minio.values.yaml minio dev-backend
$ kubectl get pods
NAME                                       READY   STATUS    RESTARTS   AGE
keycloak-dev-backend-keycloak-0            1/1     Running   0          10m
keycloak-dev-backend-keycloak-pg-0         1/1     Running   0          10m
minio-dev-backend-minio-0                  1/1     Running   0          20s
postgresql-dev-backend-postgres-0          1/1     Running   0          5m32s
redis-dev-backend-redis-7cbd7c7bb8-6d74c   1/1     Running   0          7m15s
```

The important information you will need from here is:

```yaml
AWS_S3_ENDPOINT_URL: https://drive-minio.127.0.0.1.nip.io
AWS_S3_ACCESS_KEY_ID: dinum
AWS_S3_SECRET_ACCESS_KEY: password
AWS_STORAGE_BUCKET_NAME: drive-media-storage
AWS_S3_SIGNATURE_VERSION: s3v4
STORAGES_STATICFILES_BACKEND: django.contrib.staticfiles.storage.StaticFilesStorage
MEDIA_BASE_URL: https://drive.127.0.0.1.nip.io
```    

## Deployment

Now you are ready to deploy Drive. To deploy Drive, you need to provide all previous information to the helm chart.

```
$ helm repo add drive https://suitenumerique.github.io/drive/
$ helm repo update
$ helm install drive drive/drive -f docs/examples/helm/drive.values.yaml
$ kubectl get pods
NAME                                        READY   STATUS      RESTARTS   AGE
drive-backend-76d4dcb84f-c8hg5              1/1     Running     0          13m
drive-backend-celery-857c7bc58-q84ls        1/1     Running     0          13m
drive-backend-celery-beat-7d57859dd-74q4h   1/1     Running     0          13m
drive-backend-configure-wopi-66f9j          0/1     Completed   0          13m
drive-backend-createsuperuser-hpxkz         0/1     Completed   0          13m
drive-backend-migrate-jh7q4                 0/1     Completed   0          13m
drive-frontend-7f6957986d-9hwd5             1/1     Running     0          13m
keycloak-dev-backend-keycloak-0             1/1     Running     0          39m
keycloak-dev-backend-keycloak-pg-0          1/1     Running     0          39m
minio-dev-backend-minio-0                   1/1     Running     0          29m
postgresql-dev-backend-postgres-0           1/1     Running     0          34m
redis-dev-backend-redis-7cbd7c7bb8-6d74c    1/1     Running     0          36m

```

## Test your deployment

In order to test your deployment you have to log in to your instance. If you exclusively use our examples you can run:

```
$ kubectl get ingress
NAME                              CLASS    HOSTS                                  ADDRESS     PORTS     AGE
drive                             <none>   drive.127.0.0.1.nip.io                 localhost   80, 443   14m
drive-admin                       <none>   drive.127.0.0.1.nip.io                 localhost   80, 443   14m
drive-media                       <none>   drive.127.0.0.1.nip.io                 localhost   80, 443   14m
drive-media-preview               <none>   drive.127.0.0.1.nip.io                 localhost   80, 443   14m
keycloak-dev-backend-keycloak     <none>   drive-keycloak.127.0.0.1.nip.io        localhost   80, 443   40m
minio-dev-backend-minio-api       <none>   drive-minio.127.0.0.1.nip.io           localhost   80, 443   29m
minio-dev-backend-minio-console   <none>   drive-minio-console.127.0.0.1.nip.io   localhost   80, 443   29m

```

You can use Drive at https://drive.127.0.0.1.nip.io. The provisionning user in keycloak is drive/drive.
