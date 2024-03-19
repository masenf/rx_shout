"""Handle Google Auth."""
import reflex as rx

import reflex_google_auth
from ..state import State


def auth_error_callout() -> rx.Component:
    """Rendered when there is a user auth error."""
    return rx.cond(
        State.auth_error,
        rx.callout.root(
            rx.callout.icon(rx.icon("alert-triangle", size=20)),
            rx.callout.text(State.auth_error),
            size="1",
            color_scheme="red",
            variant="soft",
        ),
    )


def google_auth_button():
    return rx.box(
        reflex_google_auth.google_oauth_provider(
            reflex_google_auth.google_login(
                on_success=[reflex_google_auth.GoogleAuthState.on_success, State.reload_after_login],
            ),
        ),
        box_shadow="rgba(0, 0, 0, 0.16) 0px 10px 36px 0px, rgba(0, 0, 0, 0.06) 0px 0px 0px 1px",  # noqa
        opacity="0.7",
        overflow="hidden",
        border_radius="10px",
        width="200px",
    )
