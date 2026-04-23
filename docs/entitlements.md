# Entitlements

The entitlements system provides a pluggable backend architecture for checking user permissions and capabilities within the Drive application. It allows you to determine whether users can access the application and perform specific actions like uploading files.

## Overview

The entitlements system is designed to be flexible and extensible. It uses a backend pattern where different implementations can be configured based on your deployment needs. The system automatically discovers and exposes all methods starting with `can_` from the configured backend through the API.

## Architecture

The entitlements system consists of:

- **Base Backend Interface** (`EntitlementsBackend`): An abstract base class that defines the required interface
- **Backend Implementations**: Concrete implementations that provide the actual entitlement checking logic
- **Backend Factory**: A utility function that loads and caches the configured backend
- **API Endpoint**: A REST API endpoint that exposes entitlements to authenticated users

### Backend Interface

All entitlements backends must inherit from `EntitlementsBackend` and implement at least two abstract methods:

- `can_access(user)`: Can the OIDC logged in user access the app?
- `can_upload(user)`: Can the OIDC logged in user upload new files?

These methods need to return a dictionary with a `result` key (boolean) indicating if the user can upload files. Optionally includes a `message` key for user-facing messages.

The API endpoint automatically discovers and exposes all methods starting with `can_` from the backend, making it easy to extend with additional permission checks.

## Available Backends

### Static Backend

The `StaticEntitlementsBackend` is the default backend used for development and testing. It returns the values passed to its constructor via `ENTITLEMENTS_BACKEND_PARAMETERS["entitlements"]`. When no parameters are provided, it grants access for every check; configure them to simulate denied users (staging, demos, manual QA).

**Configuration:**

```python
ENTITLEMENTS_BACKEND = "core.entitlements.backends.static.StaticEntitlementsBackend"
ENTITLEMENTS_BACKEND_PARAMETERS = {
    "entitlements": {
        "can_upload": {"result": True},
        "can_access": {"result": True},
    },
}
```

### DeployCenter Backend

The `DeployCenterEntitlementsBackend` integrates with an external [DeployCenter](https://github.com/suitenumerique/st-deploycenter) entitlements service to check user permissions based on their account email and other OIDC claims.

It fetches entitlements from an external API using a cache mechanism.

## API Endpoint

### GET /api/v1.0/entitlements/

Returns all entitlements for the authenticated user.

**Authentication:** Required (user must be authenticated)

**Response Format:**

```json
{
  "can_access": {
    "result": true
  },
  "can_upload": {
    "result": false,
    "message": "Upload quota exceeded"
  }
}
```

**Response Fields:**

- Each key corresponds to a method name from the backend (methods starting with `can_`)
- Each value is a dictionary containing:
  - `result` (boolean): Whether the user has the permission
  - `message` (string, optional): A user-facing message explaining the result

**Example Request:**

```bash
curl -H "Authorization: Bearer <token>" \
     https://drive.example.com/api/v1.0/entitlements/
```

**Example Response:**

```json
{
  "can_access": {
    "result": true
  },
  "can_upload": {
    "result": true
  }
}
```

## Creating Custom Backends

To create a custom entitlements backend:

1. **Create a new backend class** that inherits from `EntitlementsBackend`:

```python
from core.entitlements.backends.base import EntitlementsBackend

class CustomEntitlementsBackend(EntitlementsBackend):
    """Custom entitlements backend."""

    def can_access(self, user):
        """
        Check if a user can access the app.

        Returns:
            dict: Dictionary with 'result' key (bool) and optional 'message' key (str)
        """
        # Your custom logic here
        return {"result": True}

    def can_upload(self, user):
        """
        Check if a user can upload files.

        Returns:
            dict: Dictionary with 'result' key (bool) and optional 'message' key (str)
        """
        # Your custom logic here
        return {"result": False, "message": "Uploads are disabled"}
```

2. **Configure the backend** in your settings:

```python
ENTITLEMENTS_BACKEND = "your_module.backends.custom.CustomEntitlementsBackend"
ENTITLEMENTS_BACKEND_PARAMETERS = {
    # Any parameters your backend needs - passed as kwargs to the constructor
}
```

3. **Accept parameters via constructor** (if needed):

Constructor parameters are generic, use the one you need and add custom ones if needed.

Example:

```python
from core.entitlements.backends.base import EntitlementsBackend

class CustomEntitlementsBackend(EntitlementsBackend):
    def __init__(self, **kwargs):
        self.api_url = kwargs["api_url"]
        # ...

    def can_access(self, user):
        # Use self.api_url, self.api_key, etc.
        return {"result": True}
```
