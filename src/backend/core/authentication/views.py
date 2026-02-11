"""Drive core authentication views."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.http import HttpResponseRedirect

from lasuite.oidc_login.views import (
    OIDCAuthenticationCallbackView as LaSuiteOIDCAuthenticationCallbackView,
)

from core.authentication.exceptions import UserCannotAccessApp


class OIDCAuthenticationCallbackView(LaSuiteOIDCAuthenticationCallbackView):
    """
    Custom view for handling the authentication callback from the OpenID Connect (OIDC) provider.
    Handles the callback after authentication from the identity provider (OP).
    Verifies the state parameter and performs necessary authentication actions.
    """

    def get(self, request):
        try:
            return super().get(request)
        except UserCannotAccessApp as exc:
            safe_message = str(exc).replace("\r", " ").replace("\n", " ").strip()
            if len(safe_message) > 200:
                safe_message = safe_message[:200]

            parsed = urlsplit(self.failure_url)
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            query["auth_error"] = "user_cannot_access_app"
            if safe_message:
                query["auth_error_message"] = safe_message

            merged_query = urlencode(query, doseq=True)
            failure_url = urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    merged_query,
                    parsed.fragment,
                )
            )
            return HttpResponseRedirect(failure_url)
