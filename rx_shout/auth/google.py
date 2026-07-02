"""Google OIDC authentication provider."""

import reflex as rx
import reflex_enterprise as rxe


class GoogleAuthState(rxe.auth.OIDCAuthState, rx.State):
    """Auth state for logging in with a Google account."""

    __provider__ = "google"
