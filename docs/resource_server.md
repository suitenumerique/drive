# Use Drive as a Resource Server

Drive implements resource server, so it means it can be used from an external app to perform some operation using the dedicated API.

> **Note:** This feature might be subject to future evolutions. The API endpoints, configuration options, and behavior may change in future versions.

## Prerequisites

In order to activate the resource server on Drive you need to setup the following environement variables

```
OIDC_RESOURCE_SERVER_ENABLED=True
OIDC_OP_URL=
OIDC_OP_INTROSPECTION_ENDPOINT=
OIDC_RS_CLIENT_ID=
# Refs-only secret configuration (do not set OIDC_RS_CLIENT_SECRET directly)
OIDC_RS_CLIENT_SECRET_FILE=/run/secrets/drive_oidc_rs_client_secret
# or:
OIDC_RS_CLIENT_SECRET_ENV=DRIVE_OIDC_RS_CLIENT_SECRET
OIDC_RS_AUDIENCE_CLAIM=
OIDC_RS_ALLOWED_AUDIENCES=
```

It implements the resource server using `django-lasuite`, see the [documentation](https://github.com/suitenumerique/django-lasuite/blob/main/documentation/how-to-use-oidc-resource-server-backend.md)

## Customise allowed routes

Configure the `EXTERNAL_API` setting to control which routes and actions are available in the external API. Set it via the `EXTERNAL_API` environment variable (as JSON) or in Django settings.

External API routes are disabled by default. You must explicitly enable at
least one resource to expose `/external_api/v1.0/...` routes.

Default configuration:

```python
EXTERNAL_API = {
    "items": {
        "enabled": False,
        "actions": [],
    },
    "item_access": {
        "enabled": False,
        "actions": [],
    },
    "item_invitation": {
        "enabled": False,
        "actions": [],
    },
    "users": {
        "enabled": False,
        "actions": [],
    }
}
```

**Endpoints:**

- `items`: Controls `/external_api/v1.0/items/`. Available actions: `list`, `retrieve`, `create`, `update`, `partial_update`, `destroy`, `children`, `upload_ended`, `move`, `restore`, `trashbin`, `hard_delete`, `tree`, `breadcrumb`, `link_configuration`, `favorite`, `media_auth`, `wopi`
- `item_access`: Controls `/external_api/v1.0/items/{id}/accesses/`. Available actions: `list`, `retrieve`, `create`, `update`, `partial_update`, `destroy`
- `item_invitation`: Controls `/external_api/v1.0/items/{id}/invitations/`. Available actions: `list`, `retrieve`, `create`, `update`, `partial_update`, `destroy`
- `users`: Controls `/external_api/v1.0/users/`. Available actions: `list`, `retrieve`, `create`, `update`, `partial_update`, `destroy`, `get_me`

Each endpoint has `enabled` (boolean) and `actions` (list of allowed actions). Only actions explicitly listed are accessible.

## Request Drive

In order to request drive from an external resource provider, you need to implement the basic setup of `django-lasuite` [Using the OIDC Authentication Backend to request a resource server](https://github.com/suitenumerique/django-lasuite/blob/main/documentation/how-to-use-oidc-call-to-resource-server.md)

Then you can requests some routes that are available at `/external_api/v1.0/*`, here are some examples of what you can do.

#### Upload a file

Here is an example of a view that create a file on the main workspace in Drive.

```python
    @method_decorator(refresh_oidc_access_token)
    def upload_file(self, request):
        """
        Create a new file in the main workspace.
        """

        # Get the access token from the session
        access_token = request.session.get('oidc_access_token')

        # Get the main workspace
        response = requests.get(
            f"{settings.DRIVE_API}/items/",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        items = data['results']
        main_workspace = None
        for item in items:
            if item['main_workspace']:
                main_workspace = item
                break

        if not main_workspace:
            return drf.response.Response(status=404, data={"error": "No main workspace found"})

        # Create a new file in the main workspace
        response = requests.post(
            f"{settings.DRIVE_API}/items/{main_workspace['id']}/children/",
            json={
                "type": "file",
                "filename": "test.txt",
            },
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        )
        response.raise_for_status()
        item = response.json()
        policy = item['policy']

        # Upload file content using the presigned URL
        import os
        sample_file_path = os.path.join(os.path.dirname(__file__), "sample.txt")
        with open(sample_file_path, "rb") as f:
            upload_response = requests.put(
                policy,
                data=f.read(),
                headers={
                    "Content-Type": "text/plain",
                    "x-amz-acl": "private"
                }
            )
            upload_response.raise_for_status()

        # Tell the Drive API that the upload is ended
        response = requests.post(
            f"{settings.DRIVE_API}/items/{item['id']}/upload-ended/",
            json={},
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        )
        response.raise_for_status()

        return drf.response.Response(data)
```

#### Create a new folder

Using the same logic as the previous example, you can create a folder in the main workspace.

```python
response = requests.post(
    f"{settings.DRIVE_API}/items/{main_workspace['id']}/children/",
    json={
        "type": "folder",
        "title": "My folder",
    },
    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
)
```

#### Get user information

The same way, you can use the /me endpoint to get user information.

```python
response = requests.get(
    "{settings.DRIVE_API}/users/me/",
    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
)
```
