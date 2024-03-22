"""The form for submitting new entries."""

import reflex as rx

from ..state import State, UserInfoState
from .image_upload import image_upload_component


def form_error_callout() -> rx.Component:
    """Rendered when there is a form validation error."""
    return rx.cond(
        State.form_error,
        rx.callout.root(
            rx.callout.icon(rx.icon("alert-triangle", size=20)),
            rx.callout.text(State.form_error),
            size="1",
            color_scheme="red",
            variant="soft",
            width="100%",
        ),
    )


def submission_form() -> rx.Component:
    """The form for submitting new entries."""
    return rx.form(
        rx.vstack(
            rx.heading(
                rx.hstack(
                    rx.icon("megaphone", size=25),
                    rx.cond(
                        State.topic,
                        rx.cond(
                            State.topic.description,
                            State.topic.description,
                            State.topic.name,
                        ),
                        "Shout Your Thoughts Into the Void",
                    ),
                    align="center",
                ),
                size="4",
            ),
            form_error_callout(),
            rx.hstack(
                rx.input.root(
                    rx.input.slot(rx.icon("user", size=20)),
                    rx.input(
                        value=UserInfoState.user_info.author.name,
                        read_only=True,
                    ),
                    width="100%",
                ),
                rx.input.root(
                    rx.input.slot(rx.icon("at_sign", size=20)),
                    rx.input(
                        value=UserInfoState.user_info.email,
                        read_only=True,
                    ),
                    width="100%",
                ),
                rx.icon_button(
                    rx.icon("log-out", size=20),
                    on_click=State.logout_and_reset,
                    color_scheme="gray",
                    type="button",
                ),
                width="100%",
            ),
            rx.input.root(
                rx.input.slot(rx.icon("text", size=20)),
                rx.input(placeholder="Enter text here...", id="text"),
                width="100%",
            ),
            image_upload_component(),
            rx.hstack(
                rx.button(
                    "Reload",
                    rx.icon("refresh-cw", size=20),
                    on_click=State.load_entries,
                    type="button",
                    color_scheme="gray",
                ),
                rx.spacer(),
                rx.button("Post", rx.icon("send", size=20)),
                width="100%",
            ),
            gap="1em",
        ),
        on_submit=State.handle_submit,
    )
