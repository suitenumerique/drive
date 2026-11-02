"""Utils for testing the external API authenticated through Menshen token exchange."""

MENSHEN_SERVER_URL = "https://menshen.example.com"
MENSHEN_INTROSPECTION_URL = f"{MENSHEN_SERVER_URL}/auth/token/introspect/"
MENSHEN_CLIENT_ID = "drive"
MENSHEN_CLIENT_SECRET = "some_client_secret"

MENSHEN_SUB = "specific-sub"
MENSHEN_EMAIL = "specific@example.com"
MENSHEN_TOKEN = "some_exchanged_token"
MENSHEN_SOURCE = "meet"

MENSHEN_REQUIRED_SCOPES = {
    "items": {
        "list": "drive:item:list",
        "retrieve": "drive:item:retrieve",
        "create": "drive:item:create",
        "children": {
            "GET": "drive:item:list-children",
            "POST": "drive:item:create-children",
        },
        "upload_ended": "drive:item:upload-ended",
    },
}

ALL_SCOPES = (
    "drive:item:list drive:item:retrieve drive:item:create "
    "drive:item:list-children drive:item:create-children drive:item:upload-ended"
)


def menshen_backend_setup(settings):
    """Configure Drive as a Menshen client, leaving the resource server off."""
    settings.MENSHEN_ENABLED = True
    settings.MENSHEN_SERVER_URL = MENSHEN_SERVER_URL
    settings.MENSHEN_CLIENT_ID = MENSHEN_CLIENT_ID
    settings.MENSHEN_CLIENT_SECRET = MENSHEN_CLIENT_SECRET
    settings.MENSHEN_REQUIRED_SCOPES = MENSHEN_REQUIRED_SCOPES
    settings.OIDC_RESOURCE_SERVER_ENABLED = False


def menshen_introspection_response(**overrides):
    """Build an active introspection response, in the shape Menshen returns."""

    return {
        "active": True,
        "sub": MENSHEN_SUB,
        "email": MENSHEN_EMAIL,
        "scope": ALL_SCOPES,
        "aud": [MENSHEN_CLIENT_ID],
        "client_id": MENSHEN_SOURCE,
        "token_type": "urn:ietf:params:oauth:token-type:access_token",
        **overrides,
    }
