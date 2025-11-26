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

### Dummy Backend

The `DummyEntitlementsBackend` is the default backend used for development and testing. It always returns `True` for all entitlement checks.

**Configuration:**

```python
ENTITLEMENTS_BACKEND = "core.entitlements.dummy_entitlements_backend.DummyEntitlementsBackend"
ENTITLEMENTS_BACKEND_PARAMETERS = {}
```

### ANCT Backend

The `ANCTEntitlementsBackend` is a good example of what you can achieve with entitlements. It integrates with an external ANCT entitlements service to check user permissions based on their SIRET (French business identifier) and other account information.

It fetches entitlements from an external API using a cache mecanism.

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
from core.entitlements.entitlements_backend import EntitlementsBackend

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
ENTITLEMENTS_BACKEND = "your_module.custom_entitlements_backend.CustomEntitlementsBackend"
ENTITLEMENTS_BACKEND_PARAMETERS = {
    # Any parameters your backend needs
}
```

3. **Access parameters** (if needed):

```python
from django.conf import settings

class CustomEntitlementsBackend(EntitlementsBackend):
    def __init__(self):
        self.params = settings.ENTITLEMENTS_BACKEND_PARAMETERS

    def can_access(self, user):
        # Use self.params to access configuration
        return {"result": True}
```
