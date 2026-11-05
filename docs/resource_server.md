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
OIDC_RS_CLIENT_SECRET=
OIDC_RS_AUDIENCE_CLAIM=
OIDC_RS_ALLOWED_AUDIENCES=
```

It implements the resource server using `django-lasuite`, see the [documentation](https://github.com/suitenumerique/django-lasuite/blob/main/documentation/how-to-use-oidc-resource-server-backend.md)

## Customise allowed routes

Configure the `EXTERNAL_API` setting to control which routes and actions are available in the external API. Set it via the `EXTERNAL_API` environment variable (as JSON) or in Django settings.

Default configuration:

```python
EXTERNAL_API = {
    "items": {
        "enabled": True,
        "actions": ["create", "list", "retrieve", "children", "upload_ended"],
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
        "enabled": True,
        "actions": ["get_me"],
    }
}
```

**Endpoints:**

- `items`: Controls `/external_api/v1.0/items/`. Available actions: `list`, `retrieve`, `create`, `update`, `partial_update`, `destroy`, `children`, `upload_ended`, `move`, `restore`, `trashbin`, `hard_delete`, `tree`, `breadcrumb`, `link_configuration`, `favorite`, `media_auth`, `wopi`, `convert`, `favorite_list`, `recents`, `deletion_info`, `search`, `batch_share`, `unlock`, `restrict`, `leave`, `download`, `export`, `duplicate`
- `item_access`: Controls `/external_api/v1.0/items/{id}/accesses/`. Available actions: `list`, `retrieve`, `create`, `update`, `partial_update`, `destroy`
- `item_invitation`: Controls `/external_api/v1.0/items/{id}/invitations/`. Available actions: `list`, `retrieve`, `create`, `update`, `partial_update`, `destroy`

Each endpoint has `enabled` (boolean) and `actions` (list of allowed actions). Only actions explicitly listed are accessible.

## Customise created item attributes per audience

Configure the `EXTERNAL_API_AUD_ITEM_ATTRIBUTES` setting to apply extra attributes to items
created through the external API, depending on the token audience of the request (the claim
configured by `OIDC_RS_AUDIENCE_CLAIM`). Set it via the `EXTERNAL_API_AUD_ITEM_ATTRIBUTES`
environment variable (as JSON) or in Django settings.

```python
EXTERNAL_API_AUD_ITEM_ATTRIBUTES = {
    "some_audience": {
        "quota_excluded": True,
    },
}
```

With this configuration, every item created by a request authenticated with the
`some_audience` audience is excluded from its creator's storage quota computation.
Audiences without an entry keep the default item attributes.

## Permissions

A request acts on behalf of the user identified by the access token. Drive checks that:

- The token holds at least one scope of `OIDC_RS_SCOPES`.
- The token audience is in `OIDC_RS_ALLOWED_AUDIENCES`.
- The action is listed in `EXTERNAL_API`, otherwise the API returns a 403. With `enabled: False`, the route does not exist and returns a 404.
- The user's role on the item allows the action, with the same rules as the main API.

There are no rights specific to the calling application, and scopes do not restrict actions.

### Roles

| Role | Rights |
|---|---|
| `reader` | Read |
| `editor` | Read, edit, and delete a non-root item they created |
| `administrator` | Read, edit, delete a non-root item, and share |
| `owner` | Same as `administrator`, and can delete a root item and grant or change the `owner` role |

A role is set on an item, either a file or a folder, and applies to its descendants. The access role is the highest one among the item and its ancestors. A link that reaches the user can raise it up to `link_role` (`reader` or `editor`), but never gives the right to share, see `link_configuration`.

`GET /external_api/v1.0/items/{id}/` returns the access role of the token's user in `user_role`, which ignores links, and the allowed actions in `abilities`, which take links into account. It does not require enabling `item_access`.

### Accesses

Accesses target existing users, through `/external_api/v1.0/items/{id}/accesses/`.

| Action | Rule |
|---|---|
| `list` | Any access role on the item, other users get an empty list. Accesses include those inherited from ancestors. Readers and editors only see administrators and owners. |
| `retrieve` | The access's own user, or an administrator or owner |
| `create` | Administrator or owner. The new role must be higher than the one the target user already has on the item or its ancestors, otherwise the API returns a 400. Sends an email to the target user. |
| `update`, `partial_update` | Administrator or owner. A role lower than the inherited one returns a 403. Setting the role inherited from ancestors deletes the explicit access and returns a 204. |
| `destroy` | Administrator or owner |

Only an owner can grant the `owner` role, or change or delete an owner access. The last owner of a root item cannot be changed or deleted.

### Invitations

Invitations target emails with no Drive account yet, through `/external_api/v1.0/items/{id}/invitations/`. All actions require an administrator or owner, except `list` which returns an empty list to other users. Only an owner can invite with the `owner` role. Creating an invitation for the email of a registered user returns a 400, unless `OIDC_ALLOW_DUPLICATE_EMAILS` is enabled.

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

        import os
        sample_file_path = os.path.join(os.path.dirname(__file__), "sample.txt")

        # Reserve the file size before requesting an upload authorization.
        response = requests.post(
            f"{settings.DRIVE_API}/items/{main_workspace['id']}/children/",
            json={
                "type": "file",
                "filename": "test.txt",
                "size": os.path.getsize(sample_file_path),
            },
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        )
        response.raise_for_status()
        item = response.json()
        policy = item['policy']

        # Upload the raw file using the size-bound presigned URL
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

#### Share an item

In `EXTERNAL_API`, enable `item_access` and `item_invitation` with the `create` action, and add `list` to `users`. The user search tolerates typos in emails, so compare the returned email with the expected one before sharing. It only returns active users: the invitation returns a 400 for the email of an inactive account, unless `OIDC_ALLOW_DUPLICATE_EMAILS` is enabled.

```python
headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
email = "colleague@example.com"

response = requests.get(f"{settings.DRIVE_API}/users/", params={"q": email}, headers=headers)
response.raise_for_status()
user = next((user for user in response.json() if user["email"] == email), None)

if user:
    # Give an access to an existing user
    response = requests.post(
        f"{settings.DRIVE_API}/items/{item['id']}/accesses/",
        json={"user_id": user["id"], "role": "editor"},
        headers=headers,
    )
else:
    # Invite an email with no account yet
    response = requests.post(
        f"{settings.DRIVE_API}/items/{item['id']}/invitations/",
        json={"email": email, "role": "editor"},
        headers=headers,
    )
response.raise_for_status()
```

#### Get user information

The same way, you can use the /me endpoint to get user information.

```python
response = requests.get(
    "{settings.DRIVE_API}/users/me/",
    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
)
```
