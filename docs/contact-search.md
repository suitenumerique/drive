# Contact search: suggest people and groups from La Suite Contacts

The share modal suggests contacts as the user types
(`GET /api/v1.0/contacts/?q=`). A contact is a user or a group. Who it
suggests depends on the contact search backend: django-lasuite's
`lasuite.contact_search` (`LASUITE_CONTACT_SEARCH` setting, see its
[guide](https://github.com/suitenumerique/django-lasuite/blob/main/documentation/how-to-use-contact-search-backend.md)):

| Backend | Suggests | Query |
|---|---|---|
| `core.contact_search.LocalContactSearchBackend` (default) | Drive's active users, matched on their email | 5 characters at least |
| `lasuite.contact_search.backends.lasuite_contacts.LaSuiteContactsBackend` | The user's contacts and groups in [La Suite Contacts](https://github.com/suitenumerique/contacts), ranked by how often the user shares with them | 1 character |

The frontend keeps calling Drive, which calls Contacts.

## How the La Suite Contacts backend works

- Drive calls Contacts' `GET /external_api/v1.0/search/` with the user's own
  OIDC access token (stored in the session at login).
- Each result is a user or a group (`kind`), in Contacts' order:
  - an address that belongs to a Drive user comes back as that user:
    sharing creates an access;
  - any other address comes back as `{"id": email, "email": email, ...}`:
    the share modal turns it into an invitation;
  - an address of an inactive account, or of several accounts, is left out;
  - a group comes back with its name and member count.
- Drive has no groups of its own. The share modal shows a group as one row
  and, when it is shared, replaces it by its members
  (`GET /api/v1.0/contacts/groups/{id}/members/`, which reads Contacts'
  `GET /external_api/v1.0/groups/{id}/members/`). Each member gets their own
  access or invitation. A backend without groups (the local one) never
  suggests any, so an app that can't show groups has nothing to expand.
- After an access, an invitation, a batch share or a group pick, Drive reports
  it to Contacts (`POST /external_api/v1.0/interactions/`, kind `share`), so
  these contacts rank higher next time. A failed report never fails the share.
- If Contacts can't answer the search (down, slow, token refused, no token),
  the fallback backend answers (`CONTACT_SEARCH_FALLBACK_BACKEND`, Drive's
  users by default), so the share modal keeps working. A
  group whose members can't be listed answers 503: the modal says so and
  shares with nobody.

### One connection, kept open

The share modal searches on every keystroke (debounced). Drive keeps its HTTP
connection to Contacts open between calls (`httpx`, one client per gunicorn
worker), so a keystroke doesn't pay for a new TCP and TLS handshake.

- Each worker of each pod has its own connections (5 kept open at most): a
  worker that receives no search for a while lets them expire and opens a new
  one on the next keystroke.
- A connection idle longer than `keepalive_expiry` (50 s by default) is closed
  by Drive. Keep it below the idle timeout of what sits between Drive and
  Contacts (ingress, load balancer; often 60 s): otherwise Drive may send on a
  connection the server is closing. A request that fails to connect is
  retried once.
- Inside a cluster, prefer Contacts' internal service address as `base_url`
  (e.g. `http://contacts-backend.contacts.svc:8000`): no TLS, no ingress, and
  no ingress idle timeout to stay under.

## Configure Drive

```shell
CONTACT_SEARCH_BACKEND=lasuite.contact_search.backends.lasuite_contacts.LaSuiteContactsBackend
CONTACT_SEARCH_BACKEND_PARAMETERS={"base_url": "https://contacts.example.org", "timeout": 2}
# Optional: who answers when Contacts can't (Drive's users by default);
# lasuite.contact_search.backends.dummy.DummyContactSearchBackend finds nobody
# CONTACT_SEARCH_FALLBACK_BACKEND=core.contact_search.LocalContactSearchBackend

# The user's access token is needed, and must be refreshed
OIDC_STORE_ACCESS_TOKEN=True
OIDC_STORE_REFRESH_TOKEN=True
OIDC_STORE_REFRESH_TOKEN_KEY=<key generated with bin/fernetkey>

# One request per keystroke (debounced): raise the burst rate
API_USERS_LIST_THROTTLE_RATE_BURST=120/minute
```

Parameters of the La Suite Contacts backend:

| Parameter | Default | |
|---|---|---|
| `base_url` | (required) | Contacts' address |
| `timeout` | `2` | Seconds to wait for Contacts |
| `verify_ssl` | `true` | Check Contacts' TLS certificate |
| `keepalive_expiry` | `50` | Seconds an idle connection is kept open for reuse (see above) |
| `vendor_prefix` | `numerique.gouv.fr` | Contacts' `JSCONTACT_VENDOR_PREFIX`, which names a group's member count in its cards |
| `max_group_members` | `1000` | Most members shared with when a group is picked |

## Configure Contacts and the identity provider

- Contacts must accept tokens issued to Drive: `drive` in Contacts'
  `OIDC_RS_ALLOWED_AUDIENCES`, and `share` in the kinds Drive may report
  (Contacts' default `EXTERNAL_API`).
- Drive's access tokens must name Contacts in their audience (in Keycloak, an
  audience mapper on the `drive` client with `contacts` as included client
  audience). Otherwise Contacts' token introspection answers "inactive" and
  Drive falls back to the local search.

## Local development

Drive and Contacts must trust the same identity provider. The simplest is to
log in to Drive through the Contacts dev realm, which has a `drive` client
with the audience mapper:

```shell
# env.d/development/common.local
OIDC_OP_JWKS_ENDPOINT=http://host.docker.internal:8975/realms/contacts/protocol/openid-connect/certs
OIDC_OP_AUTHORIZATION_ENDPOINT=http://localhost:8975/realms/contacts/protocol/openid-connect/auth
OIDC_OP_TOKEN_ENDPOINT=http://host.docker.internal:8975/realms/contacts/protocol/openid-connect/token
OIDC_OP_USER_ENDPOINT=http://host.docker.internal:8975/realms/contacts/protocol/openid-connect/userinfo
OIDC_OP_LOGOUT_ENDPOINT=http://localhost:8975/realms/contacts/protocol/openid-connect/logout
OIDC_RP_CLIENT_ID=drive
OIDC_RP_CLIENT_SECRET=ThisIsAnExampleKeyForDevPurposeOnly

CONTACT_SEARCH_BACKEND=lasuite.contact_search.backends.lasuite_contacts.LaSuiteContactsBackend
CONTACT_SEARCH_BACKEND_PARAMETERS={"base_url": "http://host.docker.internal:8971"}
OIDC_STORE_ACCESS_TOKEN=True
OIDC_STORE_REFRESH_TOKEN=True
OIDC_STORE_REFRESH_TOKEN_KEY=<key generated with bin/fernetkey>
```

Log in to Drive as `user1` / `user1`: the share modal suggests `user1`'s
contacts and groups from the Contacts demo data.
