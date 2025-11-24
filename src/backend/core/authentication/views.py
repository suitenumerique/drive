"""Drive core authentication views."""

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
        except UserCannotAccessApp:
            return HttpResponseRedirect(
                self.failure_url + "?auth_error=user_cannot_access_app"
            )
