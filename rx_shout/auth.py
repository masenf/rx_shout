import reflex as rx
import reflex_enterprise as rxe


class GoogleAuthState(rxe.auth.OIDCAuthState, rx.State):
    __provider__ = "google"
