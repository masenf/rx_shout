"""Handle Google Auth."""

import reflex as rx

from ..state import UserState


def auth_error_callout() -> rx.Component:
    """Rendered when there is a user auth error."""
    return rx.cond(
        UserState.auth_error,
        rx.callout.root(
            rx.callout.icon(rx.icon("triangle_alert", size=20)),
            rx.callout.text(UserState.auth_error),
            size="1",
            color_scheme="red",
            variant="soft",
        ),
    )


def google_auth_button():
    return rx.box(
        rx.button(
            rx.icon("log-in", size=20),
            "Sign in with Google",
            on_click=rx.redirect("/login"),
            width="100%",
        ),
        box_shadow="rgba(0, 0, 0, 0.16) 0px 10px 36px 0px, rgba(0, 0, 0, 0.06) 0px 0px 0px 1px",  # noqa
        opacity="0.7",
        overflow="hidden",
        border_radius="10px",
        width="200px",
    )
