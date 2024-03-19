"""This is an shoutbox-like app for posting text and images."""

import reflex as rx
import reflex_google_auth

from .components.entry import entry_view
from .components.google_auth import (
    auth_error_callout,
    google_auth_button,
)
from .components.form import submission_form
from .state import State


@rx.page(
    title="rx_shout",
    description="A shoutbox-like app for posting text and images.",
    on_load=State.on_load,
)
def index() -> rx.Component:
    return rx.fragment(
        rx.color_mode.button(rx.color_mode.icon(), float="right"),
        rx.center(
            rx.vstack(
                rx.card(
                    rx.cond(
                        reflex_google_auth.GoogleAuthState.token_is_valid & State.user_info.enabled,
                        submission_form(),
                        rx.flex(
                            auth_error_callout(),
                            rx.spacer(),
                            google_auth_button(),
                            justify="end",
                            width="100%",
                            on_click=State.set_form_error(""),
                        ),
                    ),
                    width="100%",
                ),
                rx.vstack(
                    rx.foreach(
                        State.entries,
                        entry_view,
                    ),
                    gap="2em",
                    margin_y="2em",
                    width="100%",
                ),
                width=["100vw", "75vw", "75vw", "50vw", "50vw"],
            ),
            width="100%",
        ),
    )


app = rx.App()
